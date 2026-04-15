from datetime import date, datetime, timedelta
from hashlib import md5
from random import Random
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, params
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.user import User
from app.schemas.campaign import CampaignInsightResponse, CampaignMockResponse, CampaignSummaryResponse
from app.utils.auth import get_current_user
from app.utils.gemini_service import gemini_service

router = APIRouter()

PlatformType = Literal["google_ads", "meta_ads"]

PLATFORM_CONFIG = {
    "google_ads": {
        "account_prefix": "GA-",
        "objectives": ["leads", "sales", "traffic"],
        "names": [
            "Search - Conversao",
            "Performance Max - E-commerce",
            "Remarketing - Carrinho",
        ],
    },
    "meta_ads": {
        "account_prefix": "META-",
        "objectives": ["awareness", "engagement", "sales"],
        "names": [
            "Reels - Topo de Funil",
            "Catalogo - Dynamic Ads",
            "Lookalike - Conversao",
        ],
    },
}


def _get_user_client(db: Session, user_id: str, client_id: str) -> Client:
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.user_id == user_id)
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado para este usuario",
        )
    return client


def _seed_from(*parts: str) -> int:
    base = "|".join(parts).encode("utf-8")
    return int(md5(base).hexdigest()[:8], 16)


def _build_campaigns_for_client(
    client_id: Optional[str],
    client_name: str,
    platform: PlatformType,
    days: int,
) -> List[CampaignMockResponse]:
    config = PLATFORM_CONFIG[platform]
    results: List[CampaignMockResponse] = []
    for idx, name in enumerate(config["names"]):
        seed = _seed_from(client_id or "demo", platform, str(idx))
        rng = Random(seed)
        budget = round(rng.uniform(1200, 12000), 2)
        spent = round(rng.uniform(budget * 0.25, budget * 0.9), 2)
        impressions = rng.randint(12000, 240000)
        clicks = rng.randint(max(300, impressions // 150), max(600, impressions // 18))
        conversions = rng.randint(15, max(20, clicks // 4))
        ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0
        cpc = round(spent / clicks, 2) if clicks else 0.0
        cpm = round((spent / impressions) * 1000, 2) if impressions else 0.0

        start_date = date.today() - timedelta(days=days + rng.randint(1, 18))
        status_value = ["active", "paused", "active"][idx % 3]
        account_suffix = str(seed)[-6:]

        results.append(
            CampaignMockResponse(
                id=f"{platform}_{client_id or 'demo'}_{idx}",
                client_id=client_id,
                client_name=client_name,
                platform=platform,
                platform_account_id=f"{config['account_prefix']}{account_suffix}",
                name=name,
                status=status_value,
                objective=config["objectives"][idx % len(config["objectives"])],
                budget=budget,
                daily_budget=round(budget / max(days, 1), 2),
                spend=spent,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                ctr=ctr,
                cpc=cpc,
                cpm=cpm,
                start_date=start_date,
                source="mock",
                updated_at=datetime.utcnow(),
            )
        )
    return results


@router.get("/", response_model=List[CampaignMockResponse])
def list_campaigns(
    client_id: Optional[str] = Query(default=None),
    platform: Optional[PlatformType] = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Garantir compatibilidade com chamadas internas
    if isinstance(client_id, (params.Query, params.Param)): client_id = None
    if isinstance(platform, (params.Query, params.Param)): platform = None
    if isinstance(days, (params.Query, params.Param)): days = 7
    platforms: List[PlatformType] = (
        [platform] if platform else ["google_ads", "meta_ads"]
    )
    campaigns: List[CampaignMockResponse] = []

    persisted_query = (
        db.query(Campaign, Client.name.label("client_name"))
        .join(Client, Client.id == Campaign.client_id)
        .filter(Client.user_id == current_user.id)
    )
    if client_id:
        persisted_query = persisted_query.filter(Campaign.client_id == client_id)
    if platform:
        persisted_query = persisted_query.filter(Campaign.platform == platform)
    persisted_rows = persisted_query.all()

    if persisted_rows:
        return [
            CampaignMockResponse(
                id=row.Campaign.id,
                client_id=row.Campaign.client_id,
                client_name=row.client_name,
                platform=row.Campaign.platform,
                platform_account_id=row.Campaign.platform_account_id or "",
                name=row.Campaign.name,
                status=row.Campaign.status,
                objective=row.Campaign.objective or "traffic",
                budget=row.Campaign.budget,
                daily_budget=row.Campaign.daily_budget,
                spend=row.Campaign.spend,
                impressions=row.Campaign.impressions,
                clicks=row.Campaign.clicks,
                conversions=row.Campaign.conversions,
                ctr=row.Campaign.ctr,
                cpc=row.Campaign.cpc,
                cpm=row.Campaign.cpm,
                start_date=row.Campaign.start_date,
                end_date=row.Campaign.end_date,
                source="synced",
                updated_at=row.Campaign.updated_at,
            )
            for row in persisted_rows
        ]

    if client_id:
        client = _get_user_client(db, current_user.id, client_id)
        for pf in platforms:
            campaigns.extend(
                _build_campaigns_for_client(
                    client_id=client.id,
                    client_name=client.name,
                    platform=pf,
                    days=days,
                )
            )
        return campaigns

    user_clients = db.query(Client).filter(Client.user_id == current_user.id).all()
    if user_clients:
        for client in user_clients:
            for pf in platforms:
                campaigns.extend(
                    _build_campaigns_for_client(
                        client_id=client.id,
                        client_name=client.name,
                        platform=pf,
                        days=days,
                    )
                )
        return campaigns

    for pf in platforms:
        campaigns.extend(
            _build_campaigns_for_client(
                client_id=None,
                client_name="Conta Demo",
                platform=pf,
                days=days,
            )
        )
    return campaigns


@router.get("/summary", response_model=CampaignSummaryResponse)
def get_campaign_summary(
    client_id: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna métricas agregadas para o dashboard."""
    try:
        query = (
            db.query(Campaign)
            .join(Client, Client.id == Campaign.client_id)
            .filter(Client.user_id == current_user.id)
        )
        if client_id:
            query = query.filter(Campaign.client_id == client_id)

        campaigns = query.all()
        
        # Se não houver dados reais, gerar de mocks para preencher o dashboard
        if not campaigns:
            # Usar a lógica existente de list_campaigns para obter mocks
            mock_campaigns = list_campaigns(
                client_id=client_id, 
                platform=None, # IMPORTANTE: explicitar None para evitar passar o objeto Query
                days=days, 
                db=db, 
                current_user=current_user
            )
            
            total_spend = sum((float(c.spend or 0.0)) for c in mock_campaigns)
            total_impressions = sum((int(c.impressions or 0)) for c in mock_campaigns)
            total_clicks = sum((int(c.clicks or 0)) for c in mock_campaigns)
            total_conversions = sum((float(c.conversions or 0.0)) for c in mock_campaigns)
            
            avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
            
            return CampaignSummaryResponse(
                total_spend=round(total_spend, 2),
                total_impressions=total_impressions,
                total_clicks=total_clicks,
                total_conversions=total_conversions,
                avg_ctr=round(avg_ctr, 2),
                avg_cpc=round(avg_cpc, 2),
                campaign_count=len(mock_campaigns),
                period_days=days
            )

        # Agregação de dados reais
        total_spend = sum((float(c.spend or 0.0)) for c in campaigns)
        total_impressions = sum((int(c.impressions or 0)) for c in campaigns)
        total_clicks = sum((int(c.clicks or 0)) for c in campaigns)
        total_conversions = sum((float(c.conversions or 0.0)) for c in campaigns)
        
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0

        return CampaignSummaryResponse(
            total_spend=round(total_spend, 2),
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            avg_ctr=round(avg_ctr, 2),
            avg_cpc=round(avg_cpc, 2),
            campaign_count=len(campaigns),
            period_days=days
        )
    except Exception as e:
        import traceback
        print(f"ERROR in get_campaign_summary: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao processar métricas: {str(e)}"
        )


@router.get("/insights", response_model=List[CampaignInsightResponse])
def get_campaign_insights(
    client_id: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera insights baseados em IA para o cliente ou conta demo."""
    # Obter dados de campanhas (reais ou mocks)
    campaigns = list_campaigns(
        client_id=client_id,
        platform=None,
        days=days,
        db=db,
        current_user=current_user
    )

    # Converter para lista de dicionários para o Gemini
    campaigns_data = []
    for c in campaigns:
        campaigns_data.append({
            "name": c.name,
            "clicks": c.clicks,
            "impressions": c.impressions,
            "spend": c.spend,
            "conversions": c.conversions
        })

    # Chamar serviço do Gemini
    insights = gemini_service.generate_marketing_insights(campaigns_data)
    
    return [
        CampaignInsightResponse(
            client_id=client_id,
            platform="google_ads", # Temporário, pode ser dinâmico
            title=ins.get("title", "Aviso"),
            message=ins.get("message", ""),
            priority=ins.get("priority", "medium")
        )
        for ins in insights
    ]
