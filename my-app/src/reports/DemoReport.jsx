import React, { useState } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import ReportDetail from './ReportDetail';
import { exportReport } from './exportReport';

export default function DemoReport({ aiConfigured, demoAIEnabled = false }) {
  const [scenario, setScenario] = useState('leads');
  const [title, setTitle] = useState('Relatório de campanhas');
  const [clientName, setClientName] = useState('Estúdio Horizonte');
  const [agencyName, setAgencyName] = useState('');
  const [agencyAnalysis, setAgencyAnalysis] = useState('');
  const [nextSteps, setNextSteps] = useState('');
  const [agencyLogo, setAgencyLogo] = useState('');
  const [clientLogo, setClientLogo] = useState('');
  const [accentColor, setAccentColor] = useState('#245be8');
  const [selected, setSelected] = useState(['demo-0', 'demo-1']);
  const [metrics, setMetrics] = useState(['spend', 'impressions', 'clicks', 'leads']);
  const options = [['spend','Investimento'],['impressions','Impressões'],['clicks','Cliques'],['leads','Leads'],['purchases','Compras'],['revenue','Receita atribuída'],['ctr','CTR'],['cpc','CPC'],['cpl','Custo por lead'],['roas','ROAS']];
  const logo = (event, setter) => { const file = event.target.files?.[0]; if (!file) return; if (!['image/png','image/jpeg'].includes(file.type) || file.size > 128*1024) {setError('Use uma logo PNG ou JPEG de até 128 KB.'); event.target.value=''; return;} const reader = new FileReader(); reader.onload = () => setter(reader.result); reader.readAsDataURL(file); };
  const [includeAI, setIncludeAI] = useState(false);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const canUseAI = Boolean(aiConfigured && demoAIEnabled);
  const generate = async () => {
    setBusy(true); setError(''); setReport(null);
    try {
      if (!selected.length || !metrics.length || !title.trim() || !clientName.trim()) { setError('Informe cliente e título e selecione ao menos uma campanha e uma métrica.'); return; }
      const { data } = await api.post('/reports/demo', { scenario, include_ai: includeAI && canUseAI, title, client_name: clientName, campaign_metrics: Object.fromEntries(selected.map(id => [id, metrics])), agency_name: agencyName, agency_analysis: agencyAnalysis, next_steps: nextSteps, agency_logo: agencyLogo || null, client_logo: clientLogo || null, accent_color: accentColor });
      setReport(data);
    } catch (err) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Não foi possível gerar a demonstração.');
    } finally { setBusy(false); }
  };
  const download = async (id, print) => {
    setExporting(true); setError('');
    try { await exportReport(id, print, report.rendered_html); }
    catch (err) { setError(err.message || 'Falha na exportação.'); }
    finally { setExporting(false); }
  };
  return <section className="space-y-4 border border-blue-400/30 bg-blue-950/70 rounded-xl p-5">
    <div><h2 className="font-semibold text-blue-100 text-lg">Laboratório de relatórios + Cérebro IA</h2>
      <p className="text-sm text-blue-200 mt-1">Teste sem conectar anúncios. Dados fictícios, isolados dos seus clientes e do histórico real.</p></div>
    <div className="grid gap-3 md:grid-cols-2">
      <label className="text-sm text-slate-200">Nome do cliente fictício<input maxLength={120} value={clientName} onChange={e => setClientName(e.target.value)} className="block w-full mt-1 rounded-md border p-2 bg-card" /></label>
      <label className="text-sm text-slate-200">Título do relatório<input maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className="block w-full mt-1 rounded-md border p-2 bg-card" /></label>
      <label className="text-sm text-slate-200">Nome da agência (opcional)<input maxLength={120} value={agencyName} onChange={e => setAgencyName(e.target.value)} className="block w-full mt-1 rounded-md border p-2 bg-card" /></label>
      <label className="text-sm text-slate-200">Cor da capa <input type="color" value={accentColor} onChange={e => setAccentColor(e.target.value)} /></label>
      <label className="text-sm text-slate-200">Logo da agência (PNG/JPEG até 128 KB)<input type="file" accept="image/png,image/jpeg" onChange={e => logo(e, setAgencyLogo)} className="block w-full" /></label>
      <label className="text-sm text-slate-200">Logo do cliente (PNG/JPEG até 128 KB)<input type="file" accept="image/png,image/jpeg" onChange={e => logo(e, setClientLogo)} className="block w-full" /></label>
      <label className="text-sm text-slate-200">Análise da agência<textarea maxLength={3000} value={agencyAnalysis} onChange={e => setAgencyAnalysis(e.target.value)} className="block w-full mt-1 rounded-md border p-2 bg-card" /></label>
      <label className="text-sm text-slate-200">Próximos passos<textarea maxLength={3000} value={nextSteps} onChange={e => setNextSteps(e.target.value)} className="block w-full mt-1 rounded-md border p-2 bg-card" /></label>
    </div>
    <fieldset className="report-config-block"><legend>Campanhas fictícias</legend>{[['demo-0','Prospecção'],['demo-1','Remarketing']].map(([id,label]) => <label key={id} className="inline-flex gap-2 mr-5"><input type="checkbox" checked={selected.includes(id)} onChange={() => setSelected(v => v.includes(id) ? v.filter(x => x !== id) : [...v,id])} />{label}</label>)}</fieldset>
    <fieldset className="report-config-block"><legend>Métricas para as campanhas selecionadas</legend><p>As métricas indisponíveis no cenário escolhido aparecem como não informadas.</p><div className="report-metric-options">{options.map(([key,label]) => <label key={key}><input type="checkbox" checked={metrics.includes(key)} onChange={() => setMetrics(v => v.includes(key) ? v.filter(x => x !== key) : [...v,key])} />{label}</label>)}</div></fieldset>
    <label className="block text-sm text-slate-200">Cenário demonstrativo
      <select className="block w-full mt-1 rounded-md border p-2 bg-card" value={scenario} disabled={busy || exporting}
        onChange={(e) => { setScenario(e.target.value); setReport(null); }}>
        <option value="leads">Leads · CPL e comparação de períodos</option>
        <option value="sales">Vendas · receita, compras e ROAS</option>
        <option value="limited">Dados parciais · sem conversões ou receita</option>
        <option value="zero">Zero resultados · sem divisão por zero</option>
      </select>
    </label>
    <label className="flex gap-2 items-center text-sm text-slate-200">
      <input type="checkbox" checked={includeAI && canUseAI} disabled={!canUseAI || busy}
        onChange={(e) => setIncludeAI(e.target.checked)} /> Gerar análise real pela IA sobre os dados fictícios
    </label>
    <p className="text-xs text-slate-300">{canUseAI ? 'IA habilitada pelo administrador: essa opção consome créditos e não usa a cota diária por cliente.' : 'IA paga desativada no laboratório. Teste os relatórios de métricas gratuitamente, sem chamar o modelo.'}</p>
    <Button disabled={busy || exporting} onClick={generate}>{busy ? 'Preparando demonstração...' : 'Gerar demonstração'}</Button>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {report && <ReportDetail report={report} onClose={() => setReport(null)} onExport={download} exporting={exporting} />}
  </section>;
}
