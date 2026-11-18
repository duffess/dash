from html import escape
from math import ceil, floor, log10
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
            blocks.append(f'<p class="bullet">• {line[2:]}</p>')
        elif line:
            blocks.append(f"<p>{line}</p>")
    return "".join(blocks)


def dot_scale(value, limit=150):
    """Choose a readable 1/2/5 scale, bounding the number of marks."""
    if value <= 0:
        return 1
    minimum = max(value / limit, 1)
    magnitude = 10 ** floor(log10(minimum))
    return next(factor * magnitude for factor in (1, 2, 5, 10) if factor * magnitude >= minimum)


def render_report_html(report) -> str:
    from app.utils.report_metrics import enrich_snapshot, METRICS
    snapshot = enrich_snapshot(report.snapshot)

    def text(value):
        return escape(str(value if value is not None else "Não informado"))

    def number(value, keep_decimals=False):
        result = f"{float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return result[:-3] if not keep_decimals and float(value).is_integer() else result

    def display(key, value, currency=None):
        if value is None:
            return "Não informado"
        fmt = METRICS[key][1]
        prefix = text("R$" if currency == "BRL" else currency or "Moeda n/i") + " " if fmt == "money" else ""
        suffix = "%" if fmt == "percent" else "x" if fmt == "ratio" else ""
        return prefix + number(value, keep_decimals=fmt in ("money", "percent", "ratio")) + suffix

    platform_names = {"meta_ads": "Meta Ads", "google_ads": "Google Ads"}
    status_names = {"active": "Ativa", "paused": "Pausada", "ended": "Encerrada", "archived": "Arquivada", "deleted": "Excluída"}
    names = {"leads": ("lead", "leads"), "purchases": ("compra", "compras"),
             "conversions": ("conversão da plataforma", "conversões da plataforma"),
             "clicks": ("clique", "cliques"), "impressions": ("impressão", "impressões")}
    demo = snapshot.get("source") == "demo"
    badge = "DEMONSTRAÇÃO / DADOS FICTÍCIOS" if demo else "DADOS SINCRONIZADOS"
    logo = snapshot.get('agency_logo', '')
    logo_html = f'<img class="agency-logo" alt="Logo da agência" src="{text(logo)}">' if re.fullmatch(r'data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=]+', logo) else ''
    client_logo = snapshot.get('client_logo', '')
    client_logo_html = f'<img class="agency-logo" alt="Logo do cliente" src="{text(client_logo)}">' if re.fullmatch(r'data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=]+', client_logo) else ''
    accent = snapshot.get('accent_color', '')
    accent = accent if re.fullmatch(r'#[0-9a-fA-F]{6}', accent) else '#245be8'
    agency_name = f'<p class="agency-brand">Preparado por {text(snapshot["agency_name"])}</p>' if snapshot.get('agency_name') else ''
    accounts = []
    for account in snapshot["accounts"]:
        values = account["metrics"]
        currency = account.get("currency")
        platform = text(platform_names.get(account.get("platform"), account.get("platform")))
        primary = next((key for key in names if key in values), None)
        primary_html = ''
        if primary is not None:
            value = values[primary]
            singular, plural = names[primary]
            label = singular if value == 1 else plural
            scale = dot_scale(value)
            full = floor(value / scale)
            remainder = value - full * scale
            marks = '<span class="dot"></span>' * full
            if remainder > 1e-9:
                pct = min(100, remainder / scale * 100)
                marks += f'<span class="dot partial" style="--fill:{pct:.4f}%"></span>'
            chart = (f'<div class="dots" role="img" aria-label="{number(value)} {text(label)}; cada ponto completo representa {number(scale)} {text(singular if scale == 1 else plural)}">{marks}</div>'
                     f'<p class="dot-legend">● 1 ponto completo = {number(scale)} {text(singular if scale == 1 else plural)}. O último ponto pode ser proporcional.</p>') if value else '<p class="dot-legend">Nenhum resultado registrado para este indicador no período.</p>'
            phrase = f'No período, as campanhas selecionadas registraram {number(value)} {label} nesta conta.'
            primary_html = f'<div class="hero-metric"><span class="kicker">{text(METRICS[primary][0])}</span><strong>{display(primary, value, currency)}</strong><p>{text(phrase)}</p></div>{chart}'
        rest = ''.join(f'<div class="stat"><span>{text(METRICS[k][0])}</span><strong>{display(k,v,currency)}</strong></div>' for k,v in values.items() if k != primary)
        account_id = text(account.get("account_id") or "Conta não informada")
        group = [row for row in snapshot['campaigns'] if (row.get('platform'), row.get('account_id'), row.get('currency')) == (account.get('platform'), account.get('account_id'), currency) and 'spend' in row['metrics']]
        group.sort(key=lambda row: row['metrics']['spend'], reverse=True)
        maximum = max((row['metrics']['spend'] for row in group), default=0)
        bars = ''.join(f'<div class="bar-row"><div class="bar-label"><span>{text(row["name"])}</span><strong>{display("spend",row["metrics"]["spend"],currency)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:{row["metrics"]["spend"]/maximum*100:.2f}%"></div></div></div>' for row in group[:5]) if maximum else ''
        chart = f'<div class="spend-chart"><span class="kicker">Investimento por campanha</span><p class="dot-legend">Até cinco campanhas desta conta, em valores absolutos.</p>{bars}</div>' if bars else ''
        accounts.append(f'<section class="account"><div class="section-top"><span>01 / RESUMO DA CONTA</span><span>{platform} · {account_id}</span></div>{primary_html or "<h2>Indicadores da conta</h2><p>Sem dados completos para totalização nesta conta.</p>"}<div class="stats">{rest}</div>{chart}</section>')

    campaigns = []
    for index, row in enumerate(snapshot["campaigns"], 1):
        selected = snapshot.get("metric_selection", {}).get(row["id"])
        keys = selected if selected is not None else list(row["metrics"])
        cells = ''.join(f'<tr><td>{text(METRICS[k][0])}</td><td>{display(k,row["metrics"].get(k),row.get("currency"))}</td></tr>' for k in keys if k in METRICS)
        missing = ', '.join(METRICS[k][0] for k in (keys if selected is not None else METRICS) if k in METRICS and k not in row["metrics"])
        platform = text(platform_names.get(row.get("platform"), row.get("platform")))
        status = text(status_names.get(row.get("status"), row.get("status")))
        campaigns.append(f'<article class="campaign"><div class="campaign-top"><span class="index">{index:02}</span><div><h3>{text(row["name"])}</h3><p>{platform} · {status}</p></div></div><table><thead><tr><th>Indicador</th><th>Resultado</th></tr></thead><tbody>{cells or "<tr><td colspan=2>Sem métricas disponíveis.</td></tr>"}</tbody></table>{f"<p class=note>Não disponíveis ou não calculáveis: {text(missing)}.</p>" if missing else ""}<p class="note">Atualização: {text(row.get("synced_at"))}</p></article>')

    comparisons = ''
    if snapshot["comparisons"]:
        rows = ''.join(f'<tr><td>{text(r["campaign"])}</td><td>{text(METRICS[r["metric"]][0])}</td><td>{number(r["previous"])}</td><td>{number(r["current"])}</td><td>{number(r["change_percent"])}%</td></tr>' for r in snapshot["comparisons"])
        comparisons = f'<section><div class="section-top"><span>03 / COMPARAÇÃO</span></div><h2>Entre períodos</h2><p>Variação numérica em períodos comparáveis.</p><table><thead><tr><th>Campanha</th><th>Indicador</th><th>Anterior</th><th>Atual</th><th>Variação</th></tr></thead><tbody>{rows}</tbody></table></section>'
    analysis = f'<section><div class="section-top"><span>ANÁLISE</span></div><h2>Leitura estratégica</h2>{analysis_html(report.analysis)}<p class="note">Modelo: {text(report.ai_model)}. Sugestões exigem revisão humana.</p></section>' if report.analysis else ''
    agency_parts = []
    for key, heading in (("agency_analysis", "Análise da agência"), ("next_steps", "Próximos passos")):
        if snapshot.get(key):
            paragraphs = ''.join(f'<p>{text(line)}</p>' for line in snapshot[key].splitlines() if line.strip())
            agency_parts.append(f'<div class="agency-note"><h3>{heading}</h3>{paragraphs}</div>')
    agency = f'<section><div class="section-top"><span>LEITURA DA AGÊNCIA</span></div>{"".join(agency_parts)}</section>' if agency_parts else ''
    notes = ''.join(f'<li>{text(note)}</li>' for note in snapshot["limitations"])
    count = len(snapshot["campaigns"])
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{text(report.title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#e8ecf5;color:#10203a;font-family:Arial,sans-serif}}main{{max-width:900px;margin:24px auto;background:#f8f9fc;box-shadow:0 20px 80px #0d183322}}header{{border-top:10px solid var(--report-accent);background:#0b152a;color:white;padding:54px;min-height:490px;display:flex;flex-direction:column;justify-content:space-between}}.brand{{font-weight:900;font-size:30px;letter-spacing:-2px}}.brand span{{color:#a9c1ff}}.cover-top,.section-top{{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;font-size:10px;letter-spacing:1.4px;font-weight:700}}.cover-top{{color:#aec4f4}}header h1{{font-size:44px;line-height:1.1;letter-spacing:-1.8px;overflow-wrap:anywhere;margin:15px 0}}header h2{{font-size:26px;margin:14px 0;color:#fff}}header p{{color:#c8d5ed}}.badge{{display:inline-block;border:1px solid #809bd5;padding:7px 10px;font-size:9px;letter-spacing:1px}}section{{padding:48px 54px;border-bottom:1px solid #dbe2ef}}.section-top{{color:#245be8;border-bottom:1px solid #9eacc2;padding-bottom:14px}}h2{{font-size:30px;letter-spacing:-.8px}}h3{{margin:0;overflow-wrap:anywhere}}p,li{{line-height:1.55;font-size:13px}}.account{{background:#245be8;color:white}}.account .section-top{{color:#fff;border-color:#9db6fa}}.hero-metric{{margin:35px 0 20px}}.hero-metric strong{{display:block;font-size:72px;line-height:1.1;overflow-wrap:anywhere}}.hero-metric p{{margin:8px 0}}.kicker{{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;font-weight:bold}}.dots{{display:flex;flex-wrap:wrap;gap:5px;max-width:690px;margin:24px 0 8px}}.dot{{width:11px;height:11px;border-radius:50%;background:white;display:inline-block;flex:none}}.dot.partial{{background:linear-gradient(90deg,white var(--fill),transparent var(--fill));border:1px solid white}}.dot-legend{{font-size:11px}}.stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0;margin-top:25px;border-top:1px solid #9db6fa}}.stat{{padding:20px 14px 15px 0;border-bottom:1px solid #9db6fa;min-width:0}}.stat span{{display:block;font-size:10px;min-height:28px}}.stat strong{{display:block;font-size:21px;overflow-wrap:anywhere}}.campaign{{padding:20px 0;border-bottom:1px solid #dbe2ef;break-inside:avoid}}.campaign-top{{display:flex;gap:18px}}.campaign-top p{{color:#64748b;margin:5px 0}}.index{{color:#245be8;font-weight:bold}}table{{border-collapse:collapse;width:100%;font-size:12px;margin:15px 0}}thead{{display:table-header-group}}th,td{{padding:9px;border-bottom:1px solid #dbe2ef;text-align:left;overflow-wrap:anywhere}}th:last-child,td:last-child{{text-align:right}}tr{{break-inside:avoid}}.note{{color:#64748b;font-size:10px}}footer{{padding:32px 54px;background:#0b152a;color:white}}footer strong{{font-size:22px}}@media(max-width:600px){{header,section,footer{{padding:28px}}header h1{{font-size:32px}}.hero-metric strong{{font-size:48px}}.stats{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@page{{size:A4;margin:12mm}}@media print{{*{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}body{{background:white}}main{{margin:0;box-shadow:none}}header{{break-after:page;min-height:240mm}}section{{padding:24px 20px}}.account{{break-inside:avoid}}.campaign{{break-inside:avoid}}footer{{padding:20px}}}}
.spend-chart{{margin-top:28px;break-inside:avoid}}.bar-row{{margin:13px 0}}.bar-label{{display:flex;justify-content:space-between;gap:12px;font-size:11px}}.bar-label span{{overflow-wrap:anywhere}}.bar-track{{height:7px;background:#91aff7;margin-top:7px}}.bar-fill{{height:100%;background:white}}.agency-note{{margin-top:24px;overflow-wrap:anywhere}}.agency-note h3{{break-after:avoid}}.agency-logo{{max-width:160px;max-height:70px;object-fit:contain;object-position:left center}}.agency-brand{{font-size:12px}}@media print{{header{{min-height:245mm;height:auto}}h2,h3,.section-top{{break-after:avoid}}.campaign{{break-inside:avoid}}.campaign-top{{break-after:avoid}}.stats{{break-inside:auto}}.stat,.bar-row,.agency-note p{{break-inside:avoid}}}}
</style></head><body style="--report-accent:{accent}"><main><header><div class="cover-top"><div class="brand">DASH<span>.</span></div><span>RELATÓRIO DE PERFORMANCE</span></div><div><span class="badge">{badge}</span><h1>{text(report.title)}</h1><h2>{text(snapshot["client_name"])}</h2>{client_logo_html}<p>{text(snapshot["period_note"])}</p>{logo_html}{agency_name}</div><div class="cover-top"><span>{count} {"CAMPANHA SELECIONADA" if count == 1 else "CAMPANHAS SELECIONADAS"}</span><span>MENOS RUÍDO. MAIS CLAREZA.</span></div></header>{''.join(accounts) or '<section><h2>Sem campanhas disponíveis</h2><p>Nenhum indicador disponível para este relatório.</p></section>'}<section><div class="section-top"><span>02 / CAMPANHAS</span><span>{count} selecionadas</span></div><h2>Campanha por campanha.</h2><p>Dados disponíveis para o período informado.</p>{''.join(campaigns) or '<p>Nenhuma campanha disponível.</p>'}</section>{comparisons}{agency}{analysis}<section><div class="section-top"><span>FONTES E LIMITES</span></div><h2>Como ler estes dados.</h2><p>{text(snapshot["currency_note"])}</p><p>{text(snapshot["conversion_note"])}</p><ul>{notes}</ul></section><footer><strong>Menos ruído.<br>Mais clareza.</strong><p>{badge} · Criado em {text(report.created_at.isoformat())}</p></footer></main></body></html>'''
