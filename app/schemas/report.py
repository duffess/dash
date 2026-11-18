from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    client_id: str
    title: str = Field(default="Relatório de campanhas", min_length=1, max_length=200)
    include_ai: bool = False
    insight_id: Optional[str] = None
    campaign_metrics: Optional[dict[str, list[str]]] = None
    agency_analysis: Optional[str] = Field(default=None, max_length=3000)
    next_steps: Optional[str] = Field(default=None, max_length=3000)
    agency_name: Optional[str] = Field(default=None, max_length=120)
    agency_logo: Optional[str] = Field(default=None, max_length=180000)
    client_logo: Optional[str] = Field(default=None, max_length=180000)
    accent_color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class ReportMetricDefaults(BaseModel):
    metrics: list[str] = Field(min_length=1, max_length=20)


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
    title: str = Field(default="Relatório demonstrativo", min_length=1, max_length=200)
    client_name: str = Field(default="Estúdio Horizonte (fictício)", min_length=1, max_length=120)
    campaign_metrics: Optional[dict[str, list[str]]] = None
    agency_name: Optional[str] = Field(default=None, max_length=120)
    agency_analysis: Optional[str] = Field(default=None, max_length=3000)
    next_steps: Optional[str] = Field(default=None, max_length=3000)
    agency_logo: Optional[str] = Field(default=None, max_length=180000)
    client_logo: Optional[str] = Field(default=None, max_length=180000)
    accent_color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
