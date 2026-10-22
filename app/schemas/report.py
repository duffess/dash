from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    client_id: str
    title: str = Field(default="Relatório de campanhas", min_length=1, max_length=200)
    include_ai: bool = False
    insight_id: Optional[str] = None


class ReportSummary(BaseModel):
    id: str
    client_id: str
    client_name: str
    title: str
    created_at: datetime
    campaign_count: int
    has_analysis: bool
    period_days: int


class ReportResponse(ReportSummary):
    snapshot: dict
    analysis: Optional[str] = None
    ai_model: Optional[str] = None
    rendered_html: Optional[str] = None


class DemoReportCreate(BaseModel):
    model_config = {"extra": "forbid"}
    scenario: Literal["leads", "sales", "limited", "zero"] = "leads"
    include_ai: bool = False
