from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.client import Client
from app.models.campaign import Campaign
from app.utils.campaign_data import real_campaign_filter
from app.utils.report_metrics import enrich_snapshot


def owned_client(db: Session, user_id: str, client_id: str) -> Client:
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == user_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return client


def campaign_snapshot(db: Session, client: Client) -> dict:
    campaigns = db.query(Campaign).filter(
        Campaign.client_id == client.id, real_campaign_filter()
    ).order_by(Campaign.platform, Campaign.external_id).all()
    if not campaigns:
        raise HTTPException(status_code=400, detail="Nenhuma campanha real sincronizada. Conecte e sincronize a conta deste cliente primeiro.")
    rows = []
    for campaign in campaigns:
        rows.append({
            "id": campaign.id, "name": campaign.name, "platform": campaign.platform,
            "account_id": campaign.platform_account_id, "status": campaign.status,
            "objective": campaign.objective, "spend": campaign.spend,
            "impressions": campaign.impressions, "clicks": campaign.clicks,
            "conversions": campaign.conversions,
            "ctr": round(campaign.clicks / campaign.impressions * 100, 2) if campaign.impressions else 0,
            "cpc": round(campaign.spend / campaign.clicks, 2) if campaign.clicks else 0,
            "synced_at": campaign.last_synced_at.isoformat() if campaign.last_synced_at else None,
            "metrics": campaign.report_metrics if campaign.report_metrics is not None else {
                "spend": campaign.spend, "impressions": campaign.impressions, "clicks": campaign.clicks,
                **({"conversions": campaign.conversions} if campaign.platform == "google_ads" else {}),
            },
        })
    return enrich_snapshot({
        "version": 2, "client_id": client.id, "client_name": client.name, "period_days": 30,
        "captured_at": datetime.utcnow().isoformat(),
        "period_note": "Últimos 30 dias consultados em cada sincronização. Consulte a data de atualização de cada campanha. Não representa um histórico diário.",
        "currency_note": "Valores monetários na moeda de cada conta, ainda não identificada pelo DashFlow. Não compare gastos entre contas sem confirmar a moeda.",
        "conversion_note": "Conversões do Google seguem a configuração da conta. Leads e compras da Meta são separados quando fornecidos. Dados antigos exigem nova sincronização para detalhar os eventos.",
        "campaigns": rows,
    })
