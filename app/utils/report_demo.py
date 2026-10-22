"""Fixed, isolated examples. Never insert fictitious campaigns into the database."""
from datetime import datetime, timezone
from app.utils.report_metrics import enrich_snapshot

SCENARIOS = {"leads": "Captação de leads", "sales": "Vendas com receita", "limited": "Dados parciais", "zero": "Sem resultados"}


def demo_snapshot(scenario="leads"):
    values = {
        "leads": [{"spend": 1800, "impressions": 120000, "clicks": 3600, "leads": 90},
                  {"spend": 600, "impressions": 40000, "clicks": 800, "leads": 20}],
        "sales": [{"spend": 2000, "impressions": 90000, "clicks": 2100, "purchases": 40, "revenue": 8000},
                  {"spend": 500, "impressions": 22000, "clicks": 600, "purchases": 10, "revenue": 2300}],
        "limited": [{"impressions": 15000, "clicks": 200}, {"spend": 300, "impressions": 10000}],
        "zero": [{"spend": 100, "impressions": 3000, "clicks": 40, "leads": 0},
                 {"spend": 0, "impressions": 0, "clicks": 0}],
    }[scenario]
    rows = [dict(id=f"demo-{i}", name=name, platform="meta_ads", account_id="DEMO-001",
                 status="active", objective=scenario, currency="BRL", metrics=value,
                 synced_at="2026-10-01T00:00:00Z")
            for i, (name, value) in enumerate(zip(("Prospecção / demonstrativo", "Remarketing / demonstrativo"), values))]
    previous = [dict(r, metrics={k: round(v * 0.8, 2) for k, v in r["metrics"].items()}) for r in rows]
    return enrich_snapshot(dict(
        version=2, source="demo", client_id="demo", client_name="Estúdio Horizonte (fictício)",
        period_days=30, captured_at=datetime.now(timezone.utc).isoformat(), campaigns=rows,
        period_note=("Demonstração: 01 a 30/09/2026. Comparação: 02 a 31/08/2026 (30 dias cada)."
                     if scenario in ("leads", "sales") else "Demonstração: 01 a 30/09/2026. Sem período anterior disponível."),
        currency_note="Dados fictícios em BRL; não representam uma conta conectada.",
        conversion_note="Leads e compras são eventos distintos. Receita é atribuída, não lucro.",
        previous_period={"period_days": 30, "campaigns": previous} if scenario in ("leads", "sales") else None,
    ))
