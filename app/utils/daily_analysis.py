"""Database-backed reservation shared by workers and report/insight endpoints."""
from datetime import datetime, time, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.insight import DailyAnalysis, Insight
from app.utils.analysis_data import campaign_snapshot

BRASILIA = timezone(timedelta(hours=-3))


def daily_analysis(db, client, generate, now=None):
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(BRASILIA).date()
    start = datetime.combine(day, time.min, BRASILIA).astimezone(timezone.utc).replace(tzinfo=None)
    # Includes analyses created before this quota was deployed.
    existing = db.query(Insight).filter(
        Insight.client_id == client.id, Insight.created_at >= start,
        Insight.created_at < start + timedelta(days=1),
        Insight.snapshot.isnot(None), Insight.ai_model.isnot(None),
    ).order_by(Insight.created_at.desc()).first()
    if existing:
        return existing
    client_id = client.id
    reservation = DailyAnalysis(client_id=client_id, day=day)
    db.add(reservation)
    try:
        db.commit()  # Unique composite PK arbitrates across processes, before API call.
    except IntegrityError:
        db.rollback()
        reservation = db.get(DailyAnalysis, (client_id, day))
        if reservation and reservation.insight_id:
            return db.get(Insight, reservation.insight_id)
        raise HTTPException(status_code=409, detail="A análise deste cliente já está em andamento. Aguarde e atualize o histórico.")
    try:
        snapshot = campaign_snapshot(db, client)
        content, model = generate(snapshot)
        insight = Insight(client_id=client_id, snapshot=snapshot, content=content,
                          ai_model=model, created_at=now.astimezone(timezone.utc).replace(tzinfo=None))
        db.add(insight)
        db.flush()
        reservation.insight_id = insight.id
        db.commit()  # Save quota and evidence together, before any report creation.
        db.refresh(insight)
        return insight
    except Exception:
        db.rollback()
        db.query(DailyAnalysis).filter_by(client_id=client_id, day=day, insight_id=None).delete()
        db.commit()
        raise
