from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.config import get_settings
from app.database import get_db
from app.models.insight import Insight
from app.models.client import Client
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.ai import generate_analysis
from app.utils.daily_analysis import daily_analysis
from app.utils.analysis_data import owned_client, campaign_snapshot

router = APIRouter()


class InsightResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    content: str
    insight_type: str
    created_at: datetime
    snapshot: Optional[dict] = None
    ai_model: Optional[str] = None


def insight_response(row):
    return InsightResponse(
        id=row.id, client_id=row.client_id, client_name=row.client.name,
        content=row.content, insight_type=row.insight_type, created_at=row.created_at,
        snapshot=row.snapshot, ai_model=row.ai_model,
    )


@router.get("/status")
def ai_status(current_user: User = Depends(get_current_user)):
    settings = get_settings()
    configured = bool(settings.openai_api_key.strip())
    return {"configured": configured, "provider": "OpenAI", "model": settings.openai_model,
            "demo_ai_enabled": configured and settings.demo_ai_enabled}


@router.get("/", response_model=List[InsightResponse])
def get_global_insights(
    client_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if client_id:
        owned_client(db, current_user.id, client_id)
    query = db.query(Insight).join(Client).filter(
        Client.user_id == current_user.id, Insight.snapshot.isnot(None), Insight.ai_model.isnot(None)
    )
    if client_id:
        query = query.filter(Insight.client_id == client_id)
    return [insight_response(row) for row in query.order_by(Insight.created_at.desc()).limit(50).all()]


@router.get("/{client_id}", response_model=List[InsightResponse])
def get_insights(
    client_id: str, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_global_insights(client_id, db, current_user)


@router.post("/{client_id}/generate", response_model=InsightResponse, status_code=201)
def generate_insight(
    client_id: str, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = owned_client(db, current_user.id, client_id)
    insight = daily_analysis(db, client, generate_analysis)
    return insight_response(insight)
