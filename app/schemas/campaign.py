from datetime import date, datetime
from pydantic import BaseModel
from typing import Literal, Optional


PlatformType = Literal["google_ads", "meta_ads"]
CampaignStatus = Literal["active", "paused", "ended", "archived", "deleted", "unknown"]


class CampaignResponse(BaseModel):
    id: str
    client_id: Optional[str] = None
    client_name: str
    platform: PlatformType
    platform_account_id: str
    name: str
    status: CampaignStatus
    objective: str
    budget: float
    daily_budget: float
    spend: float
    impressions: int
    clicks: int
    conversions: float
    ctr: float
    cpc: float
    cpm: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: Literal["synced", "mock"] = "synced"
    updated_at: datetime


class CampaignInsightResponse(BaseModel):
    client_id: Optional[str] = None
    platform: PlatformType
    title: str
    message: str
    priority: Literal["low", "medium", "high"]


class CampaignSummaryResponse(BaseModel):
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: float
    avg_ctr: float
    avg_cpc: float
    campaign_count: int
    period_days: int
