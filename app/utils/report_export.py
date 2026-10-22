from html import escape
import re


def analysis_html(content: str) -> str:
    """Render a small Markdown subset without permitting raw HTML or links."""
    blocks = []
    for raw_line in content.splitlines():
        line = escape(raw_line.strip())
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        if line.startswith("#"):
            blocks.append(f"<h3>{line.lstrip(chr(35)).strip()}</h3>")
        elif line.startswith(("- ", "* ")):
            blocks.append(f"<p class=\"bullet\">• {line[2:]}</p>")
        elif line:
            blocks.append(f"<p>{line}</p>")
    return "".join(blocks)



def render_report_html(report) -> str:
    from app.utils.report_metrics import enrich_snapshot, METRICS
    snapshot = enrich_snapshot(report.snapshot)

    def text(value):
        return escape(str(value if value is not None else "Não informado"))

    def number(value):
        return f"{float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    def display(key, value, currency=None):
        if value is None:
            return "Não informado"
        fmt = METRICS[key][1]
        suffix = "%" if fmt == "percent" else "x" if fmt == "ratio" else ""
        prefix = text(currency or "Moeda n/i") + " " if fmt == "money" else ""
        return prefix + number(value) + suffix

    demo = snapshot.get("source") == "demo"
    badge = "DEMONSTRAÇÃO / DADOS FICTÍCIOS" if demo else "DADOS SINCRONIZADOS"
    definitions = snapshot["metric_definitions"]
    accounts = []
    for row in snapshot["accounts"]:
        cards = "".join(
            f'<div class="metric"><small>{text(METRICS[k][0])}</small><strong>{display(k, v, row.get("currency"))}</strong></div>'
            for k, v in row["metrics"].items()
        )
        accounts.append(f'<article><h3>{text(row["platform"])} / {text(row["account_id"])}</h3><div class="metrics">{cards or "<p>Sem indicadores completos para totalização.</p>"}</div></article>')

    campaigns = []
    for index, row in enumerate(snapshot["campaigns"], 1):
        cells = "".join(f'<tr><td>{text(METRICS[k][0])}</td><td>{display(k, v, row.get("currency"))}</td></tr>'
                        for k, v in row["metrics"].items())
        unavailable = ", ".join(label for k, (label, _) in METRICS.items() if k not in row["metrics"])
        campaigns.append(f'<article class="campaign"><span class="eyebrow">CAMPANHA {index:02d} / {text(row.get("platform"))}</span>'
                         f'<h3>{text(row["name"])}</h3><p class="muted">Objetivo: {text(row.get("objective"))} · Status: {text(row.get("status"))}</p>'
                         f'<table><thead><tr><th>Indicador disponível</th><th>Resultado</th></tr></thead><tbody>{cells}</tbody></table>'
                         f'<p class="note">Não disponíveis ou não calculáveis: {text(unavailable)}.</p>'
                         f'<p class="note">Atualização: {text(row.get("synced_at"))}</p></article>')

    comparisons = ""
    if snapshot["comparisons"]:
        rows = "".join(f'<tr><td>{text(r["campaign"])}</td><td>{text(METRICS[r["metric"]][0])}</td>'
                       f'<td>{number(r["previous"])}</td><td>{number(r["current"])}</td><td>{number(r["change_percent"])}%</td></tr>'
                       for r in snapshot["comparisons"])
        comparisons = '<section><span class="eyebrow">EVOLUÇÃO</span><h2>Comparação entre períodos</h2><p class="muted">Variação numérica, não avaliação de qualidade. Unidades conforme os indicadores das campanhas.</p><table><thead><tr><th>Campanha</th><th>Indicador</th><th>Anterior</th><th>Atual</th><th>Variação</th></tr></thead><tbody>' + rows + '</tbody></table></section>'
    analysis = ('<section class="intelligence"><span class="eyebrow">CÉREBRO IA</span><h2>Leitura estratégica</h2>'
                + analysis_html(report.analysis) + f'<p class="note">Modelo: {text(report.ai_model)}. Sugestões exigem revisão humana.</p></section>') if report.analysis else (
                '<section class="compact"><h2>Análise estratégica</h2><p>Este relatório não inclui análise IA. Nenhuma recomendação foi inventada a partir dos indicadores.</p></section>')
    notes = "".join(f"<li>{text(note)}</li>" for note in snapshot["limitations"])
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(report.title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#e8edf5;color:#0f172a;font-family:Arial,sans-serif}}
main{{max-width:900px;margin:32px auto;background:#fff}}header{{padding:52px;background:#0f172a;color:#fff;border-top:8px solid #2563eb}}
.brand{{font-size:42px;font-weight:900;letter-spacing:-2px}}.eyebrow{{display:block;break-after:avoid;font-size:11px;font-weight:bold;letter-spacing:2px;color:#2563eb}}
header .eyebrow{{color:#93c5fd}}h1{{font-size:34px;line-height:1.15;overflow-wrap:anywhere}}h2{{font-size:25px;letter-spacing:-.5px}}h3{{font-size:18px;overflow-wrap:anywhere}}
section{{padding:32px 48px;border-bottom:1px solid #e2e8f0}}p,li{{line-height:1.65;font-size:14px;overflow-wrap:anywhere}}
.muted,.note{{color:#64748b}}.note{{font-size:12px}}.badge{{display:inline-block;margin:18px 0;padding:8px 12px;background:#1e40af;color:white;font-size:11px;font-weight:bold}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.metric{{background:#f1f5f9;border-radius:8px;padding:16px;break-inside:avoid}}
.metric small{{display:block;color:#475569;margin-bottom:10px}}.metric strong{{font-size:20px;overflow-wrap:anywhere}}
article{{margin:18px 0 28px}}table{{width:100%;border-collapse:collapse;font-size:12px}}td,th{{padding:10px 8px;text-align:left;border-bottom:1px solid #e2e8f0;overflow-wrap:anywhere}}th{{background:#eff6ff;color:#1e40af}}
tr,.metric,.campaign,.compact{{break-inside:avoid}}thead{{display:table-header-group}}h2,h3{{break-after:avoid;break-before:avoid}}.intelligence{{background:#f8fafc}}
footer{{padding:28px 48px;color:#64748b;font-size:11px}}header p{{color:#cbd5e1}}
@page{{size:A4 portrait;margin:14mm}}@media print{{body{{background:white}}main{{margin:0;max-width:none}}header{{padding:28px;print-color-adjust:exact;-webkit-print-color-adjust:exact}}section{{padding:24px 0}}footer{{padding:20px 0}}.metrics{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}
@media(max-width:600px){{header,section,footer{{padding:24px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}h1{{font-size:28px}}}}
</style></head><body><main>
<header><div class="brand">DASH<span style="color:#3b82f6">.</span></div><div class="badge">{badge}</div>
<div class="eyebrow">RELATÓRIO DE PERFORMANCE</div><h1>{text(report.title)}</h1>
<p>{text(snapshot["client_name"])}</p><p>{text(snapshot["period_note"])}</p></header>
<section><span class="eyebrow">01 / VISÃO EXECUTIVA</span><h2>O que os dados mostram</h2>
<p>{len(snapshot["campaigns"])} campanhas · {len(snapshot["accounts"])} contas · {len(definitions)} tipos de indicadores disponíveis.</p>
<p class="muted">Os blocos abaixo são construídos com os dados disponíveis. Ausência de informação não é resultado zero.</p>
{''.join(accounts)}</section>
<section><span class="eyebrow">02 / DESEMPENHO</span><h2>Campanhas em detalhe</h2>{''.join(campaigns)}</section>
{comparisons}{analysis}
<section class="compact"><span class="eyebrow">TRANSPARÊNCIA</span><h2>Fontes e limites da análise</h2><p>{text(snapshot["currency_note"])}</p><p>{text(snapshot["conversion_note"])}</p><ul>{notes}</ul></section>
<footer>{badge} · Criado em {text(report.created_at.isoformat())}<br>Retrato preservado no momento da geração. Novas sincronizações não alteram relatórios já salvos.</footer>
</main></body></html>"""
