from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.insight import Insight
from app.models.client import Client
from app.models.campaign import Campaign
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.ai import generate_insights_for_campaigns

router = APIRouter()

class InsightResponse(BaseModel):
    id: str
    client_id: str
    content: str
    insight_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[InsightResponse])
def get_global_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Retorna os insights mais recentes do usuário (qualquer cliente)
    insights = (
        db.query(Insight)
        .join(Client, Client.id == Insight.client_id)
        .filter(Client.user_id == current_user.id)
        .order_by(Insight.created_at.desc())
        .limit(5)
        .all()
    )
    return insights

@router.get("/{client_id}", response_model=List[InsightResponse])
def get_insights(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verifica dono
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    insights = db.query(Insight).filter(Insight.client_id == client_id).order_by(Insight.created_at.desc()).all()
    return insights

@router.post("/{client_id}/generate", response_model=InsightResponse)
def generate_insight(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    # Busca campanhas
    campaigns = db.query(Campaign).filter(Campaign.client_id == client_id).all()
    if not campaigns:
         raise HTTPException(status_code=400, detail="Nenhuma campanha encontrada para este cliente. Conecte dados primeiro.")
         
    # Formata como dict
    camp_data = [{
        "name": c.name,
        "status": c.status,
        "spend": c.spend,
        "clicks": c.clicks,
        "conversions": c.conversions,
        "ctr": c.ctr,
        "cpc": c.cpc
    } for c in campaigns]
    
    # Roda a IA
    ai_content = generate_insights_for_campaigns(camp_data)
    
    # Salva no banco
    insight = Insight(
        client_id=client_id,
        content=ai_content,
        insight_type="general"
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    
    return insight
