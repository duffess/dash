from typing import Optional, List
import base64
import binascii
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models.client import Client
from app.models.user import User
from app.models.report import Report
from app.models.insight import Insight
from app.schemas.report import ReportCreate, ReportResponse, ReportSummary, DemoReportCreate, ReportMetricDefaults
from app.utils.report_demo import demo_snapshot, SCENARIOS
from app.utils.report_metrics import enrich_snapshot, METRICS
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from app.utils.auth import get_current_user
from app.utils.analysis_data import owned_client, campaign_snapshot
from app.utils.ai import generate_analysis
from app.utils.daily_analysis import daily_analysis
from app.utils.report_export import render_report_html

router = APIRouter()

@router.get("/metric-defaults")
def get_metric_defaults(current_user: User = Depends(get_current_user)):
    return {"metrics": current_user.report_default_metrics}

@router.put("/metric-defaults")
def save_metric_defaults(payload: ReportMetricDefaults, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if any(key not in METRICS for key in payload.metrics):
        raise HTTPException(status_code=422, detail="Métrica desconhecida.")
    current_user.report_default_metrics = list(dict.fromkeys(payload.metrics))
    db.add(current_user)
    db.commit()
    return {"metrics": current_user.report_default_metrics}


def report_summary(row):
    return dict(
        id=row.id, client_id=row.client_id, client_name=row.snapshot["client_name"],
        title=row.title, created_at=row.created_at,
        campaign_count=len(row.snapshot["campaigns"]), has_analysis=bool(row.analysis),
        period_days=row.snapshot["period_days"],
    )


def report_response(row):
    return ReportResponse(**report_summary(row), snapshot=enrich_snapshot(row.snapshot), analysis=row.analysis,
                          ai_model=row.ai_model, rendered_html=render_report_html(row))


def owned_report(db, user_id, report_id):
    row = db.query(Report).join(Client).filter(Report.id == report_id, Client.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return row


@router.get("/", response_model=List[ReportSummary])
def list_reports(
    client_id: Optional[str] = None, offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    created_from: Optional[date] = None, created_to: Optional[date] = None,
    search: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if client_id:
        owned_client(db, current_user.id, client_id)
    query = db.query(Report).join(Client).filter(Client.user_id == current_user.id)
    if client_id:
        query = query.filter(Report.client_id == client_id)
    if search and search.strip():
        term = search.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(Report.title.ilike(f'%{term}%', escape='\\'))
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=422, detail="A data inicial deve ser anterior à data final.")
    if created_from:
        query = query.filter(Report.created_at >= datetime.combine(created_from, time.min))
    if created_to:
        query = query.filter(Report.created_at <= datetime.combine(created_to, time.max))
    rows = query.order_by(Report.created_at.desc(), Report.id).offset(offset).limit(limit).all()
    return [report_summary(row) for row in rows]


@router.get("/preview")
def preview_report(client_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return campaign_snapshot(db, owned_client(db, current_user.id, client_id))


@router.post("/", response_model=ReportResponse, status_code=201)
def create_report(
    payload: ReportCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), preview_only: bool = False,
):
    client = owned_client(db, current_user.id, payload.client_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Informe o título do relatório.")
    if payload.campaign_metrics is not None:
        if not payload.campaign_metrics or any(not keys or any(k not in METRICS for k in keys) for keys in payload.campaign_metrics.values()):
            raise HTTPException(status_code=422, detail="Selecione campanhas e métricas válidas.")
        if payload.include_ai or payload.insight_id:
            raise HTTPException(status_code=422, detail="A análise de IA ainda não suporta seleção personalizada de métricas.")
    analysis, model = None, None
    if payload.insight_id:
        if payload.include_ai:
            raise HTTPException(status_code=422, detail="Escolha reutilizar uma análise ou gerar uma nova.")
        insight = db.query(Insight).filter(Insight.id == payload.insight_id, Insight.client_id == client.id).first()
        if not insight or not insight.snapshot or not insight.ai_model:
            raise HTTPException(status_code=404, detail="Análise com dados verificáveis não encontrada para este cliente.")
        snapshot, analysis, model = insight.snapshot, insight.content, insight.ai_model
    else:
        if payload.include_ai:
            insight = daily_analysis(db, client, generate_analysis)
            snapshot, analysis, model = insight.snapshot, insight.content, insight.ai_model
        else:
            snapshot = campaign_snapshot(db, client)
    if get_settings().app_env == "development" and current_user.email == "demonstracao-dash@exemplo.com":
        snapshot = dict(snapshot)
        snapshot["source"] = "demo"
        snapshot["currency_note"] = "Dados fictícios em reais (BRL); não representam uma conta conectada."
        snapshot["campaigns"] = [dict(row, currency="BRL") for row in snapshot["campaigns"]]
    if payload.campaign_metrics is not None:
        valid_ids = {row["id"] for row in snapshot["campaigns"]}
        if not set(payload.campaign_metrics).issubset(valid_ids):
            raise HTTPException(status_code=422, detail="Uma campanha não pertence a este cliente ou não está disponível.")
        snapshot = dict(snapshot)
        snapshot["campaigns"] = [row for row in snapshot["campaigns"] if row["id"] in payload.campaign_metrics]
        snapshot["metric_selection"] = {key: list(dict.fromkeys(values)) for key, values in payload.campaign_metrics.items()}
        snapshot = enrich_snapshot(snapshot)
    snapshot = dict(snapshot)
    if (payload.agency_analysis or '').strip():
        snapshot['agency_analysis'] = payload.agency_analysis.strip()
    if (payload.next_steps or '').strip():
        snapshot['next_steps'] = payload.next_steps.strip()
    if (payload.agency_name or '').strip():
        snapshot['agency_name'] = payload.agency_name.strip()
    for logo_key in ('agency_logo', 'client_logo'):
        logo = getattr(payload, logo_key)
        if not logo:
            continue
        try:
            prefix, encoded = logo.split(',', 1)
            if prefix not in ('data:image/png;base64', 'data:image/jpeg;base64'):
                raise ValueError('format')
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 128 * 1024 or not ((prefix == 'data:image/png;base64' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (prefix == 'data:image/jpeg;base64' and raw.startswith(b'\xff\xd8\xff'))):
                raise ValueError('image')
        except (ValueError, binascii.Error):
            raise HTTPException(status_code=422, detail='Use uma logo PNG ou JPEG de até 128 KB.')
        snapshot[logo_key] = logo
    if payload.accent_color:
        snapshot['accent_color'] = payload.accent_color
    if preview_only:
        report = SimpleNamespace(id="preview", client_id=client.id, title=title, snapshot=snapshot, analysis=analysis, ai_model=model, created_at=datetime.now(timezone.utc))
        return report_response(report)
    report = Report(client_id=client.id, title=title, snapshot=snapshot, analysis=analysis, ai_model=model)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report_response(report)


@router.post("/demo", response_model=ReportResponse)
def demonstration_report(payload: DemoReportCreate, current_user: User = Depends(get_current_user)):
    if payload.include_ai and not get_settings().demo_ai_enabled:
        raise HTTPException(status_code=403, detail="IA paga desativada no laboratório. Gere a demonstração sem IA.")
    snapshot = demo_snapshot(payload.scenario)
    if not payload.title.strip() or not payload.client_name.strip():
        raise HTTPException(status_code=422, detail="Informe título e nome do cliente fictício.")
    snapshot["client_name"] = payload.client_name.strip() + " [FICTÍCIO]"
    if payload.campaign_metrics is not None:
        valid_ids = {row["id"] for row in snapshot["campaigns"]}
        if not payload.campaign_metrics or not set(payload.campaign_metrics).issubset(valid_ids) or any(not values or any(key not in METRICS for key in values) for values in payload.campaign_metrics.values()):
            raise HTTPException(status_code=422, detail="Selecione campanhas e métricas válidas.")
        snapshot["campaigns"] = [row for row in snapshot["campaigns"] if row["id"] in payload.campaign_metrics]
        snapshot["metric_selection"] = payload.campaign_metrics
        snapshot = enrich_snapshot(snapshot)
    for key in ("agency_name", "agency_analysis", "next_steps", "accent_color"):
        value = getattr(payload, key)
        if value and value.strip(): snapshot[key] = value.strip()
    for key in ("agency_logo", "client_logo"):
        logo = getattr(payload, key)
        if not logo: continue
        try:
            prefix, encoded = logo.split(',', 1)
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 128 * 1024 or not ((prefix == 'data:image/png;base64' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (prefix == 'data:image/jpeg;base64' and raw.startswith(b'\xff\xd8\xff'))): raise ValueError('image')
        except (ValueError, binascii.Error):
            raise HTTPException(status_code=422, detail='Use uma logo PNG ou JPEG de até 128 KB.')
        snapshot[key] = logo
    analysis, model = generate_analysis(snapshot) if payload.include_ai else (None, None)
    row = SimpleNamespace(id="demo-" + payload.scenario, client_id="demo", snapshot=snapshot,
                          title="Demonstração / " + payload.title.strip(),
                          created_at=datetime.now(timezone.utc), analysis=analysis, ai_model=model)
    return report_response(row)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_response(owned_report(db, current_user.id, report_id))


@router.get("/{report_id}/html", response_class=HTMLResponse)
def export_report(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = owned_report(db, current_user.id, report_id)
    return HTMLResponse(render_report_html(row), headers={
        "Content-Disposition": f'attachment; filename="dashflow-report-{row.id}.html"',
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
    })


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = owned_report(db, current_user.id, report_id)
    db.delete(row)
    db.commit()
    return Response(status_code=204)
