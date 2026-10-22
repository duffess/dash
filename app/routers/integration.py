from datetime import date, datetime, timezone
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
from app.utils.meta_ads import MetaAdsService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

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


def _meta_service():
    settings = get_settings()
    return MetaAdsService(settings.meta_app_id, settings.meta_app_secret, settings.meta_redirect_uri)


def _google_service():
    settings = get_settings()
    if not all((settings.google_ads_client_id, settings.google_ads_client_secret)):
        raise HTTPException(status_code=400, detail="Configure as credenciais do Google Ads antes de sincronizar.")
    return GoogleAdsService(settings.google_ads_client_id, settings.google_ads_client_secret)


def _token(integration, meta=False):
    encrypted = integration.access_token_encrypted if meta else integration.refresh_token_encrypted
    try:
        token = decrypt_text(encrypted) if encrypted else None
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível ler a credencial. Reconecte a conta.")
    if not token or token == "mock_token":
        raise HTTPException(status_code=400, detail="Reconecte a conta para obter uma credencial válida.")
    return token


def _accounts(integration):
    try:
        if integration.platform == "meta_ads":
            return _meta_service().fetch_ad_accounts(_token(integration, meta=True))
        return _google_service().list_accessible_customers(_token(integration))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Não foi possível listar as contas. Verifique as credenciais e permissões.")


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
        
    return AccountListResponse(accounts=_accounts(integration))


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
    if "account_id" in data:
        account_id = data["account_id"]
        if not account_id or account_id not in _accounts(row):
            raise HTTPException(status_code=400, detail="Selecione uma conta disponível para esta integração.")
        if row.account_id and row.account_id != account_id:
            existing = db.query(Campaign).filter(
                Campaign.integration_id == row.id,
                Campaign.platform_account_id == row.account_id,
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail="Esta integração já tem campanhas. Use outro cliente para conectar outra conta.")
        data["status"] = "connected"
        data["sync_error"] = None
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
    if integration.status not in {"connected", "error"}:
        raise HTTPException(status_code=400, detail="Conecte a integração e selecione a conta antes de sincronizar.")
    if not integration.account_id:
        raise HTTPException(status_code=400, detail="Selecione uma conta de anúncios antes de sincronizar.")
    now = datetime.now(timezone.utc)
    try:
        if integration.platform == "google_ads":
            campaigns_data = _google_service().fetch_campaigns(integration.account_id, _token(integration))
        elif integration.platform == "meta_ads":
            campaigns_data = _meta_service().fetch_campaigns(_token(integration, meta=True), integration.account_id)
        else:
            raise HTTPException(status_code=400, detail="Plataforma não suportada.")
        for campaign_data in campaigns_data:
            for field in ("start_date", "end_date"):
                value = campaign_data.get(field)
                campaign_data[field] = date.fromisoformat(value[:10]) if isinstance(value, str) and value else value or None
    except Exception as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else "Falha ao consultar campanhas. Verifique as credenciais, permissões e conta selecionada."
        integration.sync_error = detail
        db.commit()
        raise HTTPException(status_code=exc.status_code if isinstance(exc, HTTPException) else 502, detail=detail)

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
                report_metrics=campaign_data.get("report_metrics"),
            )
            db.add(row)
        synced_count += 1

    integration.status = "connected"
    integration.last_sync_at = now
    integration.sync_error = None
    db.commit()

    return IntegrationSyncResponse(
        integration_id=integration.id,
        platform=integration.platform,
        synced_campaigns=synced_count,
        last_sync_at=now,
    )

