from datetime import date, datetime, timedelta, timezone
from hashlib import md5
from random import Random
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.database import get_db
from app.models.client import Client
from app.models.integration import ClientIntegration
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationSyncResponse,
    IntegrationUpdate,
)
from pydantic import BaseModel

class AccountListResponse(BaseModel):
    accounts: List[str]

from app.utils.auth import get_current_user
from app.utils.crypto import encrypt_text, decrypt_text
from app.utils.google_ads import GoogleAdsService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

SYNC_TEMPLATES = {
    "google_ads": {
        "names": ["Search - Brand", "Performance Max", "Remarketing - Carrinho"],
        "objectives": ["leads", "sales", "traffic"],
        "account_prefix": "GA-",
    },
    "meta_ads": {
        "names": ["Reels - Conversao", "Catalogo - DPA", "Lookalike - Prospecting"],
        "objectives": ["awareness", "engagement", "sales"],
        "account_prefix": "META-",
    },
}


def _ensure_client_owner(db: Session, client_id: str, user_id: str) -> Client:
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )
    return client


def _to_response(integration: ClientIntegration) -> IntegrationResponse:
    return IntegrationResponse(
        id=integration.id,
        client_id=integration.client_id,
        platform=integration.platform,
        account_id=integration.account_id,
        status=integration.status,
        has_access_token=bool(integration.access_token_encrypted),
        has_refresh_token=bool(integration.refresh_token_encrypted),
        expires_at=integration.expires_at,
        last_sync_at=integration.last_sync_at,
        sync_error=integration.sync_error,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


def _seed_from(*parts: str) -> int:
    base = "|".join(parts).encode("utf-8")
    return int(md5(base).hexdigest()[:8], 16)


def _generate_synced_campaigns(integration: ClientIntegration) -> list[dict]:
    """Fallback mock generator para plataformas não integradas ou contas demo."""
    template = SYNC_TEMPLATES.get(integration.platform)
    if not template:
        return []
        
    rows: list[dict] = []
    for idx, name in enumerate(template["names"]):
        seed = _seed_from(integration.id, integration.client_id, integration.platform, str(idx))
        rng = Random(seed)
        budget = round(rng.uniform(1000, 10000), 2)
        spend = round(rng.uniform(budget * 0.2, budget * 0.85), 2)
        impressions = rng.randint(8000, 220000)
        clicks = rng.randint(max(200, impressions // 180), max(500, impressions // 15))
        conversions = rng.randint(10, max(16, clicks // 5))
        ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0
        cpc = round(spend / clicks, 2) if clicks else 0.0
        cpm = round((spend / impressions) * 1000, 2) if impressions else 0.0
        external_id = f"{integration.platform}_{integration.client_id}_{idx}"
        rows.append(
            {
                "external_id": external_id,
                "name": name,
                "status": "active" if idx != 1 else "paused",
                "objective": template["objectives"][idx % len(template["objectives"])],
                "budget": budget,
                "daily_budget": round(budget / 30, 2),
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": ctr,
                "cpc": cpc,
                "cpm": cpm,
                "start_date": date.today() - timedelta(days=30 + idx * 3),
                "end_date": None,
                "platform_account_id": f"{template['account_prefix']}{str(seed)[-6:]}",
            }
        )
    return rows


def _sync_google_ads(integration: ClientIntegration, db: Session) -> list[dict] | None:
    """Executa a sincronização real com a API do Google Ads usando o SDK oficial."""
    settings = get_settings()
    if not settings.google_ads_developer_token:
        # Fallback para mocks se não houver credenciais
        return _generate_synced_campaigns(integration)

    service = GoogleAdsService(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
    )

    refresh_token = (
        decrypt_text(integration.refresh_token_encrypted)
        if integration.refresh_token_encrypted
        else None
    )

    if not refresh_token:
        integration.status = "error"
        integration.sync_error = "Refresh token ausente. Reconecte a conta."
        db.commit()
        return None

    try:
        # O SDK oficial lida com o refresh do access_token automaticamente
        return service.fetch_campaigns(integration.account_id, refresh_token)
    except Exception as e:
        logger.error(f"Erro na sincronização Google Ads: {str(e)}")
        integration.status = "error"
        integration.sync_error = str(e)
        db.commit()
        return None


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_client_owner(db, payload.client_id, current_user.id)

    existing = (
        db.query(ClientIntegration)
        .filter(
            ClientIntegration.client_id == payload.client_id,
            ClientIntegration.platform == payload.platform,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integracao para esta plataforma ja existe neste cliente",
        )

    integration = ClientIntegration(
        client_id=payload.client_id,
        platform=payload.platform,
        account_id=payload.account_id,
        status=payload.status,
        access_token_encrypted=encrypt_text(payload.access_token),
        refresh_token_encrypted=encrypt_text(payload.refresh_token) if payload.refresh_token else None,
        expires_at=payload.expires_at,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return _to_response(integration)


@router.get("/", response_model=List[IntegrationResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(Client.user_id == current_user.id)
        .all()
    )
    return [_to_response(row) for row in rows]


@router.get("/{integration_id}", response_model=IntegrationResponse)
def get_integration(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracao nao encontrada",
        )
    return _to_response(row)

@router.get("/{integration_id}/accounts", response_model=AccountListResponse)
def get_integration_accounts(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    integration = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracao nao encontrada",
        )
        
    if integration.platform != "google_ads":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas google_ads suporta listagem de contas no momento",
        )
        
    refresh_token = decrypt_text(integration.refresh_token_encrypted) if integration.refresh_token_encrypted else None
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integracao sem refresh_token, impossível listar contas",
        )
        
    settings = get_settings()
    service = GoogleAdsService(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
    )
    
    accounts = service.list_accessible_customers(refresh_token)
    return AccountListResponse(accounts=accounts)


@router.put("/{integration_id}", response_model=IntegrationResponse)
def update_integration(
    integration_id: str,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracao nao encontrada",
        )

    data = payload.model_dump(exclude_unset=True)
    if "access_token" in data:
        row.access_token_encrypted = encrypt_text(data.pop("access_token"))
    if "refresh_token" in data:
        refresh_value = data.pop("refresh_token")
        row.refresh_token_encrypted = encrypt_text(refresh_value) if refresh_value else None

    for field, value in data.items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracao nao encontrada",
        )

    db.delete(row)
    db.commit()
    return None


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
def sync_integration_campaigns(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    integration = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracao nao encontrada",
        )
    if integration.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integracao precisa estar conectada para sincronizar",
        )
    if integration.platform not in SYNC_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plataforma nao suportada para sync",
        )

    now = datetime.now(timezone.utc)
    
    # Decidir qual plataforma sincronizar
    if integration.platform == "google_ads":
        campaigns_data = _sync_google_ads(integration, db)
    elif integration.platform == "meta_ads":
        # Por enquanto o Meta Ads roda igual ao Fallback do mock (que gera DPA/Reels)
        # Quando a token graph for validada na V2, implementaremos a fetch real aqui.
        campaigns_data = _generate_synced_campaigns(integration)
    else:
        # Outras plataformas ainda usam mocks
        campaigns_data = _generate_synced_campaigns(integration)

    # Se campaigns_data for None, significa que houve um erro já registrado no _sync_google_ads
    if campaigns_data is None:
        db.refresh(integration)
        return IntegrationSyncResponse(
            integration_id=integration.id,
            platform=integration.platform,
            synced_campaigns=0,
            last_sync_at=integration.last_sync_at,
        )

    synced_count = 0
    for campaign_data in campaigns_data:
        existing = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == integration.client_id,
                Campaign.platform == integration.platform,
                Campaign.external_id == campaign_data["external_id"],
            )
            .first()
        )

        if existing:
            for field, value in campaign_data.items():
                setattr(existing, field, value)
            existing.integration_id = integration.id
            existing.last_synced_at = now
        else:
            row = Campaign(
                client_id=integration.client_id,
                integration_id=integration.id,
                platform=integration.platform,
                external_id=campaign_data["external_id"],
                platform_account_id=campaign_data["platform_account_id"],
                name=campaign_data["name"],
                status=campaign_data["status"],
                objective=campaign_data["objective"],
                budget=campaign_data.get("budget", 0),
                daily_budget=campaign_data.get("daily_budget", 0),
                spend=campaign_data["spend"],
                impressions=campaign_data["impressions"],
                clicks=campaign_data["clicks"],
                conversions=campaign_data["conversions"],
                ctr=campaign_data.get("ctr", 0),
                cpc=campaign_data.get("cpc", 0),
                cpm=campaign_data.get("cpm", 0),
                start_date=campaign_data["start_date"],
                end_date=campaign_data["end_date"],
                last_synced_at=now,
            )
            db.add(row)
        synced_count += 1

    integration.last_sync_at = now
    integration.sync_error = None
    db.commit()

    return IntegrationSyncResponse(
        integration_id=integration.id,
        platform=integration.platform,
        synced_campaigns=synced_count,
        last_sync_at=now,
    )

@router.post("/{integration_id}/mock", response_model=IntegrationSyncResponse)
def generate_mock_campaigns(
    integration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    integration = (
        db.query(ClientIntegration)
        .join(Client, Client.id == ClientIntegration.client_id)
        .filter(ClientIntegration.id == integration_id, Client.user_id == current_user.id)
        .first()
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integracao nao encontrada")

    now = datetime.now(timezone.utc)
    campaigns_data = _generate_synced_campaigns(integration)
    synced_count = 0

    for campaign_data in campaigns_data:
        existing = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == integration.client_id,
                Campaign.platform == integration.platform,
                Campaign.external_id == campaign_data["external_id"],
            )
            .first()
        )

        if existing:
            for field, value in campaign_data.items():
                setattr(existing, field, value)
            existing.integration_id = integration.id
            existing.last_synced_at = now
        else:
            row = Campaign(
                client_id=integration.client_id,
                integration_id=integration.id,
                platform=integration.platform,
                external_id=campaign_data["external_id"],
                platform_account_id=campaign_data["platform_account_id"],
                name=campaign_data["name"],
                status=campaign_data["status"],
                objective=campaign_data["objective"],
                budget=campaign_data.get("budget", 0),
                daily_budget=campaign_data.get("daily_budget", 0),
                spend=campaign_data["spend"],
                impressions=campaign_data["impressions"],
                clicks=campaign_data["clicks"],
                conversions=campaign_data["conversions"],
                ctr=campaign_data.get("ctr", 0),
                cpc=campaign_data.get("cpc", 0),
                cpm=campaign_data.get("cpm", 0),
                start_date=campaign_data["start_date"],
                end_date=campaign_data["end_date"],
                last_synced_at=now,
            )
            db.add(row)
        synced_count += 1

    integration.status = "connected"
    integration.last_sync_at = now
    db.commit()

    return IntegrationSyncResponse(
        integration_id=integration.id,
        platform=integration.platform,
        synced_campaigns=synced_count,
        last_sync_at=now,
    )

