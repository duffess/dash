"""Deterministic report contract: missing is not zero; ratios need denominators."""
from copy import deepcopy
from math import isfinite

METRICS = {
    "spend": ("Investimento", "money"), "impressions": ("Impressões", "number"),
    "clicks": ("Cliques", "number"), "conversions": ("Conversões da plataforma", "number"),
    "leads": ("Leads", "number"), "purchases": ("Compras", "number"),
    "revenue": ("Receita atribuída", "money"), "ctr": ("CTR", "percent"),
    "cpc": ("CPC", "money"), "cpm": ("CPM", "money"),
    "cpl": ("Custo por lead", "money"), "cpa": ("Custo por compra", "money"),
    "roas": ("ROAS", "ratio"),
}
BASE = ("spend", "impressions", "clicks", "conversions", "leads", "purchases", "revenue")


def valid(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0


def metrics(values):
    result = {key: values[key] for key in BASE if valid(values.get(key))}
    for name, numerator, denominator, multiplier in (
        ("ctr", "clicks", "impressions", 100), ("cpc", "spend", "clicks", 1),
        ("cpm", "spend", "impressions", 1000), ("cpl", "spend", "leads", 1),
        ("cpa", "spend", "purchases", 1), ("roas", "revenue", "spend", 1),
    ):
        if numerator in result and result.get(denominator, 0) > 0:
            result[name] = round(result[numerator] / result[denominator] * multiplier, 2)
    return result


def enrich_snapshot(snapshot):
    """Also adapts old immutable snapshots without changing their stored values."""
    data = deepcopy(snapshot)
    data.setdefault("source", "synced")
    groups = {}
    for row in data["campaigns"]:
        # An explicit metrics dictionary is authoritative, even if empty.
        row["metrics"] = metrics(row.get("metrics", row))
        row["available_metrics"] = list(row["metrics"])
        key = (row.get("platform"), row.get("account_id"), row.get("currency"))
        groups.setdefault(key, []).append(row)
    accounts = []
    for (platform, account_id, currency), rows in groups.items():
        # Do not present partial coverage as a full account total.
        totals = {k: sum(r["metrics"][k] for r in rows) for k in BASE
                  if all(k in r["metrics"] for r in rows)}
        values = metrics(totals)
        accounts.append(dict(platform=platform, account_id=account_id, currency=currency,
                             campaign_count=len(rows), metrics=values, **values))
    data["accounts"] = accounts
    data["metric_definitions"] = {k: {"label": label, "format": fmt} for k, (label, fmt) in METRICS.items()
                                  if any(k in r["metrics"] for r in data["campaigns"])}
    data["limitations"] = [
        "Indicadores ausentes não representam zero. Totais por conta exigem cobertura de todas as campanhas.",
        "CPL = investimento / leads; custo por compra = investimento / compras; ROAS = receita atribuída / investimento.",
        "Sem metas ou dados de qualidade comercial, menor custo não prova melhor resultado de negócio.",
    ]
    if not all(r.get("currency") for r in data["campaigns"]):
        data["limitations"].append("Moeda não identificada em parte dos dados; valores não são somados entre contas.")
    if not data.get("previous_period"):
        data["limitations"].append("Sem período anterior comparável: variações percentuais não são exibidas.")
    if not data.get("timeline"):
        data["limitations"].append("Sem série temporal: gráfico de evolução indisponível.")
    data["comparisons"] = []
    # Compare only matched campaign/account/currency and explicitly equivalent periods.
    previous = data.get("previous_period")
    if previous and previous.get("period_days") == data["period_days"]:
        old = {r["id"]: r for r in previous.get("campaigns", [])}
        for row in data["campaigns"]:
            before = old.get(row["id"])
            if not before or any(before.get(k) != row.get(k) for k in ("platform", "account_id", "currency")):
                continue
            for key, value in row["metrics"].items():
                prior = metrics(before.get("metrics", before)).get(key)
                if prior is not None and prior > 0:
                    data["comparisons"].append(dict(campaign=row["name"], metric=key,
                        previous=prior, current=value, change_percent=round((value / prior - 1) * 100, 2)))
    return data
