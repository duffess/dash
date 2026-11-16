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
        prefix = text("R$" if currency == "BRL" else currency or "Moeda n/i") + " " if fmt == "money" else ""
        formatted = number(value)
        if fmt == "number" and float(value).is_integer():
            formatted = formatted[:-3]
        return prefix + formatted + suffix

    demo = snapshot.get("source") == "demo"
    badge = "DEMONSTRAÇÃO / DADOS FICTÍCIOS" if demo else "DADOS SINCRONIZADOS"
    definitions = snapshot["metric_definitions"]
    accounts = []
    charts = []
    for row in snapshot["accounts"]:
        cards = "".join(
            f'<div class="metric"><small>{text(METRICS[k][0])}</small><strong>{display(k, v, row.get("currency"))}</strong></div>'
            for k, v in row["metrics"].items()
        )
        platform = {"meta_ads": "Meta Ads", "google_ads": "Google Ads"}.get(row["platform"], row["platform"])
        accounts.append(f'<article class="account"><div class="account-heading"><div><span class="eyebrow">PLATAFORMA</span><h3>{text(platform)}</h3></div><span class="account-id">{text(row["account_id"] or "Conta não informada")}</span></div><div class="metrics">{cards or "<p>Sem indicadores completos para totalização.</p>"}</div></article>')
        group = [c for c in snapshot["campaigns"] if (c.get("platform"), c.get("account_id"), c.get("currency")) == (row.get("platform"), row.get("account_id"), row.get("currency")) and "spend" in c["metrics"]]
        group.sort(key=lambda c: c["metrics"]["spend"], reverse=True)
        maximum = max((c["metrics"]["spend"] for c in group), default=0)
        if group and maximum > 0:
            bars = ''.join(f'<div class="bar-row"><div class="bar-label"><span>{text(c["name"])}</span><strong>{display("spend", c["metrics"]["spend"], row.get("currency"))}</strong></div><div class="bar-track"><div class="bar-fill" style="width:{c["metrics"]["spend"] / maximum * 100:.2f}%"></div></div></div>' for c in group[:5])
            charts.append(f'<article class="chart"><h3>{text(platform)} · {text(row["account_id"] or "Conta não informada")}</h3><p class="muted">Até cinco campanhas com maior investimento nesta conta.</p>{bars}</article>')

    campaigns = []
    for index, row in enumerate(snapshot["campaigns"], 1):
        selected_keys = snapshot.get("metric_selection", {}).get(row["id"])
        visible_keys = selected_keys if selected_keys is not None else list(row["metrics"])
        cells = "".join(f'<tr><td>{text(METRICS[k][0])}</td><td>{display(k, row["metrics"].get(k), row.get("currency"))}</td></tr>'
                        for k in visible_keys if k in METRICS)
        unavailable = ", ".join(METRICS[k][0] for k in (visible_keys if selected_keys is not None else METRICS) if k in METRICS and k not in row["metrics"])
        unavailable_note = f'<p class="note">Não disponíveis ou não calculáveis: {text(unavailable)}.</p>' if unavailable else ''
        platform = {"meta_ads": "Meta Ads", "google_ads": "Google Ads"}.get(row.get("platform"), row.get("platform"))
        status = {"active": "Ativa", "paused": "Pausada", "ended": "Encerrada", "archived": "Arquivada", "deleted": "Excluída"}.get(row.get("status"), row.get("status"))
        campaigns.append(f'<article class="campaign"><span class="eyebrow">CAMPANHA {index:02d} / {text(platform)}</span>'
                         f'<h3>{text(row["name"])}</h3><p class="muted">Objetivo: {text(row.get("objective"))} · Status: {text(status)}</p>'
                         f'<table><thead><tr><th>Indicador disponível</th><th>Resultado</th></tr></thead><tbody>{cells}</tbody></table>'
                         f'{unavailable_note}'
                         f'<p class="note">Atualização: {text(row.get("synced_at"))}</p></article>')

    comparisons = ""
    if snapshot["comparisons"]:
        rows = "".join(f'<tr><td>{text(r["campaign"])}</td><td>{text(METRICS[r["metric"]][0])}</td>'
                       f'<td>{number(r["previous"])}</td><td>{number(r["current"])}</td><td>{number(r["change_percent"])}%</td></tr>'
                       for r in snapshot["comparisons"])
        comparisons = '<section><span class="eyebrow">EVOLUÇÃO</span><h2>Comparação entre períodos</h2><p class="muted">Variação numérica, não avaliação de qualidade. Unidades conforme os indicadores das campanhas.</p><table><thead><tr><th>Campanha</th><th>Indicador</th><th>Anterior</th><th>Atual</th><th>Variação</th></tr></thead><tbody>' + rows + '</tbody></table></section>'
    analysis = ('<section class="intelligence"><span class="eyebrow">CÉREBRO IA</span><h2>Leitura estratégica</h2>'
                + analysis_html(report.analysis) + f'<p class="note">Modelo: {text(report.ai_model)}. Sugestões exigem revisão humana.</p></section>') if report.analysis else (
                '')
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
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.metric{{background:#f5f8fd;border:1px solid #e5edf8;border-radius:10px;padding:16px;break-inside:avoid}}
.metric small{{display:block;color:#475569;margin-bottom:10px}}.metric strong{{font-size:20px;overflow-wrap:anywhere}}
.account{{margin:22px 0 32px}}.account-heading{{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}}.account-heading h3{{margin:7px 0 0}}.account-id{{font-size:11px;color:#64748b;overflow-wrap:anywhere}}.chart{{background:#f7f9fd;border:1px solid #e5edf8;border-radius:14px;padding:22px;break-inside:avoid}}.chart h3{{margin:0}}.chart p{{margin:6px 0 18px;font-size:12px}}.bar-row{{margin:13px 0}}.bar-label{{display:flex;justify-content:space-between;gap:12px;font-size:12px;margin-bottom:7px}}.bar-label span{{overflow-wrap:anywhere}}.bar-label strong{{white-space:nowrap}}.bar-track{{height:8px;border-radius:99px;background:#dfe8f5;overflow:hidden}}.bar-fill{{height:100%;background:#2563eb;border-radius:99px;print-color-adjust:exact;-webkit-print-color-adjust:exact}}
article{{margin:18px 0 28px}}table{{width:100%;border-collapse:collapse;font-size:12px}}td,th{{padding:10px 8px;text-align:left;border-bottom:1px solid #e2e8f0;overflow-wrap:anywhere}}th{{background:#eff6ff;color:#1e40af}}
tr,.metric,.campaign,.compact{{break-inside:avoid}}thead{{display:table-header-group}}h2,h3{{break-after:avoid;break-before:avoid}}.intelligence{{background:#f8fafc}}
footer{{padding:28px 48px;color:#64748b;font-size:11px}}header p{{color:#cbd5e1}}
@page{{size:A4 portrait;margin:14mm}}@media print{{body{{background:white}}main{{margin:0;max-width:none}}header{{padding:28px;print-color-adjust:exact;-webkit-print-color-adjust:exact}}section{{padding:24px 0}}footer{{padding:20px 0}}.metrics{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}
@media(max-width:600px){{header,section,footer{{padding:24px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}h1{{font-size:28px}}}}
/* Report theme shared by preview and browser PDF export. */
*{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
body{{background:#090f1e;color:#edf3ff;font-family:Inter,"Segoe UI",Arial,sans-serif}}
main{{background:#101b30;box-shadow:0 25px 80px #03071366}}
header{{padding:48px;background:#0b1529;border-top:5px solid #4c7fff;border-bottom:1px solid #263751}}
.brand{{font-size:30px;letter-spacing:-1.5px;color:#fff}}
.eyebrow{{color:#9ebaff;font-size:10px;letter-spacing:1.6px}}
header .eyebrow{{color:#a6befd;margin-top:28px}}
header h1{{font-size:38px;letter-spacing:-1.2px;margin:12px 0 22px;max-width:700px}}
header p{{color:#c4d0e3;margin:6px 0;font-size:13px}}
.badge{{background:#1a315e;border:1px solid #355997;border-radius:50px;color:#cfe0ff;font-size:9px;letter-spacing:.8px;margin:18px 0 0;padding:7px 11px}}
section{{padding:34px 48px;border-color:#293953}}h2{{color:#f2f6ff;font-size:23px;margin:10px 0 12px}}h3{{color:#eff4ff}}p,li{{color:#c8d5e7}}
.muted,.note,.account-id{{color:#a9bcd1}}.metric{{background:#192942;border:1px solid #31435e;border-radius:12px;padding:16px}}
.metric small{{color:#b4c5dc;font-size:11px}}.metric strong{{color:#f8fbff;font-size:21px;letter-spacing:-.4px}}
.chart{{background:#16263e;border-color:#31435e;border-radius:14px}}.bar-label{{color:#dce8f7}}.bar-label strong{{color:#f7f9ff}}.bar-track{{background:#34435c}}.bar-fill{{background:#6794ff}}
table{{color:#d9e4f3}}td,th{{border-color:#31425a}}th{{background:#20334e;color:#b6cdff}}.intelligence{{background:#17253d}}footer{{color:#acbfd2;border-top:1px solid #293953}}
@media print{{body,main{{background:#101b30;color:#edf3ff}}main{{box-shadow:none}}header{{padding:34px}}section{{padding:26px 22px}}footer{{padding:22px}}}}
</style></head><body><main>
<header><div class="brand">DASH<span style="color:#3b82f6">.</span></div><div class="badge">{badge}</div>
<div class="eyebrow">RELATÓRIO DE PERFORMANCE</div><h1>{text(report.title)}</h1>
<p>{text(snapshot["client_name"])}</p><p>{text(snapshot["period_note"])}</p></header>
<section><span class="eyebrow">01 / VISÃO EXECUTIVA</span><h2>O que os dados mostram</h2>
<p>{len(snapshot["campaigns"])} {'campanha' if len(snapshot["campaigns"]) == 1 else 'campanhas'} · {len(snapshot["accounts"])} {'conta' if len(snapshot["accounts"]) == 1 else 'contas'} · {len(definitions)} tipos de indicadores disponíveis.</p>
<p class="muted">Os blocos abaixo são construídos com os dados disponíveis. Ausência de informação não é resultado zero.</p>
{''.join(accounts)}</section>
{('<section><span class="eyebrow">02 / DISTRIBUIÇÃO</span><h2>Onde o investimento foi aplicado</h2><p class="muted">Comparação entre campanhas da mesma conta; as barras indicam valores absolutos, não desempenho.</p>' + ''.join(charts) + '</section>') if charts else ''}
<section><span class="eyebrow">03 / DESEMPENHO</span><h2>Campanhas em detalhe</h2>{''.join(campaigns)}</section>
{comparisons}{analysis}
<section class="compact"><span class="eyebrow">TRANSPARÊNCIA</span><h2>Fontes e limites da análise</h2><p>{text(snapshot["currency_note"])}</p><p>{text(snapshot["conversion_note"])}</p><ul>{notes}</ul></section>
<footer>{badge} · Criado em {text(report.created_at.isoformat())}<br>Retrato preservado no momento da geração. Novas sincronizações não alteram relatórios já salvos.</footer>
</main></body></html>"""
