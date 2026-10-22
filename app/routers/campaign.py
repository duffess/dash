from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.user import User
from app.schemas.campaign import CampaignInsightResponse, CampaignResponse, CampaignSummaryResponse, PlatformType
from app.utils.auth import get_current_user
from app.utils.campaign_data import real_campaign_filter
from app.routers.insight import get_global_insights

router = APIRouter()


def _get_user_client(db: Session, user_id: str, client_id: str) -> Client:
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.get("/", response_model=List[CampaignResponse])
def list_campaigns(
    client_id: Optional[str] = None,
    platform: Optional[PlatformType] = None,
    days: int = Query(default=30, ge=30, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # The current storage is a 30-day snapshot, not a daily metrics history.
    if client_id:
        _get_user_client(db, current_user.id, client_id)
    query = (
        db.query(Campaign, Client.name.label("client_name"))
        .join(Client, Client.id == Campaign.client_id)
        .filter(Client.user_id == current_user.id, real_campaign_filter())
    )
    if client_id:
        query = query.filter(Campaign.client_id == client_id)
    if platform:
        query = query.filter(Campaign.platform == platform)
    return [
        CampaignResponse(
            **{field: getattr(row.Campaign, field) for field in (
                "id", "client_id", "platform", "name", "status", "budget",
                "daily_budget", "spend", "impressions", "clicks", "conversions",
                "ctr", "cpc", "cpm", "start_date", "end_date", "updated_at"
            )},
            client_name=row.client_name,
            platform_account_id=row.Campaign.platform_account_id or "",
            objective=row.Campaign.objective or "",
            source="synced",
        )
        for row in query.order_by(Campaign.name, Campaign.id).all()
    ]


@router.get("/summary", response_model=CampaignSummaryResponse)
def get_campaign_summary(
    client_id: Optional[str] = None,
    days: int = Query(default=30, ge=30, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaigns = list_campaigns(client_id, None, 30, db, current_user)
    spend = sum(c.spend for c in campaigns)
    impressions = sum(c.impressions for c in campaigns)
    clicks = sum(c.clicks for c in campaigns)
    return CampaignSummaryResponse(
        total_spend=round(spend, 2),
        total_impressions=impressions,
        total_clicks=clicks,
        total_conversions=sum(c.conversions for c in campaigns),
        avg_ctr=round(clicks / impressions * 100, 2) if impressions else 0,
        avg_cpc=round(spend / clicks, 2) if clicks else 0,
        campaign_count=len(campaigns),
        period_days=30,
    )


@router.get("/insights", response_model=List[CampaignInsightResponse])
def get_campaign_insights(
    client_id: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=30, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compatibility read endpoint; generation is POST /insights/{client_id}/generate."""
    rows = get_global_insights(client_id, db, current_user)
    return [
        CampaignInsightResponse(
            client_id=row.client_id,
            platform=row.snapshot["campaigns"][0]["platform"],
            title="Análise do cliente", message=row.content, priority="medium",
        ) for row in rows
    ]
