from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.campaign import Campaign
from app.models.report import Report
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.utils.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """cria novo cliente"""
    
    new_client = Client(
        name=client_data.name,
        email=client_data.email,
        phone=client_data.phone,
        company=client_data.company,
        user_id=current_user.id
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    return new_client

@router.get("/", response_model=List[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """lista todos os clientes do usuário"""
    
    clients = db.query(Client).filter(Client.user_id == current_user.id).all()
    return clients

@router.get('/overview')
def client_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    clients = db.query(Client.id).filter(Client.user_id == current_user.id).all()
    campaign_counts = dict(db.query(Campaign.client_id, func.count(Campaign.id)).join(Client, Campaign.client_id == Client.id).filter(Client.user_id == current_user.id).group_by(Campaign.client_id).all())
    latest_reports = dict(db.query(Report.client_id, func.max(Report.created_at)).join(Client, Report.client_id == Client.id).filter(Client.user_id == current_user.id).group_by(Report.client_id).all())
    return [{'client_id': row.id, 'campaign_count': campaign_counts.get(row.id, 0), 'last_report_at': latest_reports.get(row.id)} for row in clients]

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """busca cliente específico"""
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return client

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: str,
    client_data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """atualiza cliente"""
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Atualizar apenas campos não-nulos
    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    db.commit()
    db.refresh(client)
    
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """deleta cliente"""
    
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    db.delete(client)
    db.commit()
    
    return None
