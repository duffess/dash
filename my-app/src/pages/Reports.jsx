import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import ReportCard from '@/reports/ReportCard';
import ReportDetail from '@/reports/ReportDetail';
import { exportReport } from '@/reports/exportReport';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import DemoReport from '@/reports/DemoReport';

const METRIC_OPTIONS = [
  ['spend', 'Investimento'], ['impressions', 'Impressões'], ['clicks', 'Cliques'],
  ['conversions', 'Conversões'], ['leads', 'Leads'], ['purchases', 'Compras'],
  ['revenue', 'Receita atribuída'], ['ctr', 'CTR'], ['cpc', 'CPC'], ['cpm', 'CPM'],
  ['cpl', 'Custo por lead'], ['cpa', 'Custo por compra'], ['roas', 'ROAS'],
];
const INITIAL_METRICS = ['spend', 'impressions', 'clicks', 'ctr', 'cpc'];

export default function Reports() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const selectedClient = params.get('client_id') || '';
  const reportId = params.get('report_id');
  const [clients, setClients] = useState([]);
  const [reports, setReports] = useState([]);
  const [detail, setDetail] = useState(null);
  const [draftPreview, setDraftPreview] = useState(null);
  const [title, setTitle] = useState('Relatório de campanhas');
  const [ai, setAI] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewClient, setPreviewClient] = useState('');
  const [previewMessage, setPreviewMessage] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [detailLoading, setDetailLoading] = useState(false);
  const [defaultMetrics, setDefaultMetrics] = useState(INITIAL_METRICS);
  const [metricChoice, setMetricChoice] = useState(INITIAL_METRICS);
  const [campaignChoices, setCampaignChoices] = useState({});
  const [defaultStatus, setDefaultStatus] = useState('');
  const [agencyAnalysis, setAgencyAnalysis] = useState('');
  const [nextSteps, setNextSteps] = useState('');
  const [campaignSearch, setCampaignSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [agencyName, setAgencyName] = useState('');
  const [agencyLogo, setAgencyLogo] = useState('');
  const [clientLogo, setClientLogo] = useState('');
  const [accentColor, setAccentColor] = useState('#245be8');
  const [historySearch, setHistorySearch] = useState('');
  const [duplicate, setDuplicate] = useState(null);
  const [duplicateMessage, setDuplicateMessage] = useState('');
  const [clientLoadError, setClientLoadError] = useState('');
  const [historyError, setHistoryError] = useState('');
  const reportBlockedReason = !selectedClient ? 'Selecione um cliente para criar o relatório.'
    : !title.trim() ? 'Informe um título para o relatório.'
    : loadingPreview || (preview && previewClient !== selectedClient) ? 'Aguarde o carregamento das campanhas do cliente.'
    : !preview ? (previewMessage || 'Não foi possível carregar as campanhas deste cliente.')
    : null;
  const visibleCampaigns = (preview?.campaigns || []).filter(c => c.name.toLocaleLowerCase('pt-BR').includes(campaignSearch.trim().toLocaleLowerCase('pt-BR')));

  useEffect(() => {
    let active = true;
    api.get('/reports/metric-defaults').then(({ data }) => {
      if (active && data.metrics?.length) { setDefaultMetrics(data.metrics); setMetricChoice(data.metrics); }
    }).catch(() => { if (active) setDefaultStatus('Não foi possível carregar o padrão salvo.'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!preview) { setCampaignChoices({}); return; }
    setCampaignChoices(Object.fromEntries(preview.campaigns.map(campaign => [campaign.id, { selected: true, metrics: [...defaultMetrics] }])));
  }, [preview, defaultMetrics]);

  useEffect(() => {
    if (!duplicate || !preview || duplicate.client_id !== selectedClient || previewClient !== selectedClient) return;
    const previous = duplicate.snapshot.metric_selection || Object.fromEntries(duplicate.snapshot.campaigns.map(c => [c.id, Object.keys(c.metrics || {})]));
    const currentIds = new Set(preview.campaigns.map(c => c.id));
    const missing = Object.keys(previous).filter(id => !currentIds.has(id)).length;
    setCampaignChoices(Object.fromEntries(preview.campaigns.map(c => [c.id, {selected: Object.hasOwn(previous, c.id), metrics: previous[c.id]?.length ? previous[c.id] : [...defaultMetrics]}])));
    setDuplicateMessage(missing ? `${missing} campanha(s) do relatório anterior não estão disponíveis agora. Revise a seleção.` : 'Modelo carregado com as campanhas atuais. Revise antes de gerar.');
    setDuplicate(null);
  }, [duplicate, preview, previewClient, selectedClient, defaultMetrics]);

  const toggleMetric = (values, key) => values.includes(key) ? values.filter(value => value !== key) : [...values, key];
  const saveDefault = async () => {
    if (!metricChoice.length) { setDefaultStatus('Escolha ao menos uma métrica para salvar.'); return; }
    try {
      const { data } = await api.put('/reports/metric-defaults', { metrics: metricChoice });
      setDefaultMetrics(data.metrics); setDefaultStatus('Padrão salvo para sua conta.');
    } catch { setDefaultStatus('Não foi possível salvar o padrão. Tente novamente.'); }
  };

  useEffect(() => {
    let active = true;
    setClientLoadError('');
    api.get('/clients/').then(({data}) => { if (active) setClients(data); }).catch(() => { if (active) setClientLoadError('Não foi possível carregar os clientes.'); });
    api.get('/insights/status').then(({data}) => { if (active) setAI(data); }).catch(() => { if (active) setAI(null); });
    return () => { active = false; };
  }, [refresh]);

  useEffect(() => {
    let active = true;
    setLoading(true); setHistoryError(''); setReports([]);
    api.get('/reports/', { params: { client_id: selectedClient || undefined, created_from: dateFrom || undefined, created_to: dateTo || undefined, search: historySearch || undefined, offset: page * 20, limit: 20 } })
      .then(({ data }) => { if (active) setReports(data); })
      .catch((err) => { if (active) setHistoryError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Não foi possível carregar os relatórios.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selectedClient, page, refresh, dateFrom, dateTo, historySearch]);

  useEffect(() => {
    let active = true;
    setPreview(null); setPreviewClient(''); setPreviewMessage(''); setLoadingPreview(Boolean(selectedClient));
    if (!selectedClient) return () => { active = false; };
    api.get('/reports/preview', { params: { client_id: selectedClient } })
      .then(({ data }) => { if (active) { setPreview(data); setPreviewClient(selectedClient); } })
      .catch((err) => { if (active) setPreviewMessage(err.response?.data?.detail || 'Não foi possível consultar as campanhas.'); })
      .finally(() => { if (active) setLoadingPreview(false); });
    return () => { active = false; };
  }, [selectedClient, refresh]);

  useEffect(() => {
    let active = true;
    setDetail(null); setDetailLoading(Boolean(reportId));
    if (!reportId) return () => { active = false; };
    api.get(`/reports/${reportId}`)
      .then(({ data }) => { if (active) setDetail(data); })
      .catch(() => { if (active) setError('Não foi possível abrir o relatório.'); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [reportId]);

  const create = async (event, previewOnly = false) => {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      const campaignMetrics = Object.fromEntries(Object.entries(campaignChoices).filter(([, choice]) => choice.selected).map(([id, choice]) => [id, choice.metrics]));
      if (!Object.keys(campaignMetrics).length || Object.values(campaignMetrics).some(metrics => !metrics.length)) {
        setError('Selecione ao menos uma campanha e uma métrica para cada campanha escolhida.'); return;
      }
      const { data } = await api.post('/reports/', { client_id: selectedClient, title: title.trim(), include_ai: false, campaign_metrics: campaignMetrics, agency_analysis: agencyAnalysis, next_steps: nextSteps, agency_name: agencyName, agency_logo: agencyLogo || null, client_logo: clientLogo || null, accent_color: accentColor }, {params: {preview_only: previewOnly}});
      if (previewOnly) { setDraftPreview(data); return; }
      setDraftPreview(null);
      setPage(0); setRefresh((value) => value + 1);
      setParams({ client_id: selectedClient, report_id: data.id });
    } catch (err) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Não foi possível criar o relatório.');
    } finally { setBusy(false); }
  };

  const download = async (id, print) => {
    setExporting(true); setError('');
    try { await exportReport(id, print); }
    catch (err) { setError(err.message || 'Falha ao exportar o relatório.'); }
    finally { setExporting(false); }
  };

  const loadDuplicate = async id => {
    setError(''); setDuplicateMessage('');
    try {
      const {data} = await api.get(`/reports/${id}`);
      setTitle(data.title); setAgencyAnalysis(''); setNextSteps(''); setAgencyName(data.snapshot.agency_name || ''); setAgencyLogo(data.snapshot.agency_logo || ''); setClientLogo(data.snapshot.client_logo || ''); setAccentColor(data.snapshot.accent_color || '#245be8');
      setCampaignSearch(''); setDuplicate(data); setParams({client_id: data.client_id});
      document.getElementById('report-form')?.scrollIntoView({behavior:'smooth'});
    } catch { setError('Não foi possível carregar o relatório como modelo.'); }
  };
  const chooseLogo = (e, setter = setAgencyLogo) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!['image/png', 'image/jpeg'].includes(file.type) || file.size > 128 * 1024) {setError('Use uma logo PNG ou JPEG de até 128 KB.'); e.target.value=''; return;}
    const reader = new FileReader(); reader.onload = () => setter(reader.result); reader.onerror = () => setError('Não foi possível ler a logo.'); reader.readAsDataURL(file);
  };

  const removeReport = async report => {
    if (!window.confirm(`Excluir o relatório "${report.title}"? Esta ação não pode ser desfeita.`)) return;
    setError(''); setBusy(true);
    try {
      await api.delete(`/reports/${report.id}`);
      if (reportId === report.id) setParams(selectedClient ? {client_id: selectedClient} : {});
      if (reports.length === 1 && page > 0) setPage(p => p - 1);
      setRefresh(v => v + 1);
    } catch { setError('Não foi possível excluir o relatório. Tente novamente.'); }
    finally { setBusy(false); }
  };

  return (
    <><Helmet><title>Relatórios — DASH</title></Helmet><Layout>
      <div className="space-y-6">
        <div><h1 className="text-3xl font-bold text-white">Relatórios</h1><p className="text-slate-300 mt-1">Escolha campanhas e métricas para cada cliente.</p></div>
        {error && <div role="alert" className="border border-red-400/30 text-red-300 p-4 rounded-lg">{error} <Button variant="outline" onClick={() => setRefresh((v) => v + 1)}>Tentar novamente</Button></div>}
        {clientLoadError && <div role="alert" className="dash-panel p-4">{clientLoadError} <Button variant="outline" onClick={() => setRefresh(v => v + 1)}>Tentar novamente</Button></div>}
        <form id="report-form" onSubmit={e => create(e)} className="dash-panel p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-100">Novo relatório</h2>
          <label className="block text-slate-200">Cliente
            <select aria-label="Cliente do relatório" value={selectedClient} disabled={busy}
              onChange={(e) => { setPage(0); setCampaignSearch(''); setAgencyAnalysis(''); setNextSteps(''); setParams(e.target.value ? { client_id: e.target.value } : {}); }}
              className="block w-full border rounded-md p-2 mt-1 bg-card">
              <option value="">Todos os clientes — selecione um para criar</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </label>
          <label className="block text-slate-200">Título
            <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy}
              className="block w-full border rounded-md p-2 mt-1" />
          </label>
          <label className="block text-slate-200">Nome da agência <span className="text-slate-400">(opcional)</span><input maxLength={120} value={agencyName} onChange={e => setAgencyName(e.target.value)} className="block w-full border rounded-md p-2 mt-1" /></label>
          <label className="block text-slate-200">Logo da agência <span className="text-slate-400">(PNG ou JPEG, até 128 KB)</span><input type="file" accept="image/png,image/jpeg" onChange={e => chooseLogo(e)} className="block w-full mt-2" /></label>
          {agencyLogo && <div className="flex items-center gap-3"><img src={agencyLogo} alt="Logo selecionada" className="max-h-16 max-w-40 object-contain bg-white rounded p-1"/><Button type="button" variant="outline" onClick={() => setAgencyLogo('')}>Remover logo</Button></div>}
          <label className="block text-slate-200">Logo do cliente <span className="text-slate-400">(opcional; PNG ou JPEG, até 128 KB)</span><input type="file" accept="image/png,image/jpeg" onChange={e => chooseLogo(e, setClientLogo)} className="block w-full mt-2" /></label>
          {clientLogo && <div className="flex items-center gap-3"><img src={clientLogo} alt="Logo do cliente selecionada" className="max-h-16 max-w-40 object-contain bg-white rounded p-1"/><Button type="button" variant="outline" onClick={() => setClientLogo('')}>Remover logo do cliente</Button></div>}
          <label className="flex items-center gap-3 text-slate-200">Cor de destaque da capa <input type="color" value={accentColor} onChange={e => setAccentColor(e.target.value)} aria-label="Cor de destaque da capa" /></label>
          <p className="text-sm text-slate-400">As logos e a cor são salvas neste relatório.</p>
          <p className="text-sm text-slate-400">Período: últimos 30 dias de cada sincronização. Datas personalizadas estarão disponíveis quando houver histórico diário.</p>
          {loadingPreview && <p role="status">Consultando campanhas...</p>}
          {previewMessage && <p className="text-amber-200">{previewMessage}</p>}
          {duplicateMessage && <p role="status" className="text-blue-200">{duplicateMessage}</p>}
          {preview && <p className="text-slate-300">{preview.campaigns.length} campanhas disponíveis para este cliente.</p>}
          <fieldset className="report-config-block"><legend>Seu padrão de métricas</legend><p>Escolha as métricas que serão selecionadas automaticamente para novas campanhas. Você pode ajustar cada campanha abaixo.</p>
            <div className="report-metric-options">{METRIC_OPTIONS.map(([key,label]) => <label key={key}><input type="checkbox" checked={metricChoice.includes(key)} onChange={() => setMetricChoice(values => toggleMetric(values,key))} />{label}</label>)}</div>
            <Button type="button" variant="outline" onClick={saveDefault}>Salvar padrão</Button> <span role="status" className="report-config-status">{defaultStatus}</span>
          </fieldset>
          {preview && <fieldset className="report-config-block"><legend>Campanhas e métricas</legend><p>Escolha as campanhas e personalize as métricas de cada uma. Métricas indisponíveis não serão inventadas no relatório.</p>
            <label className="block text-slate-200">Buscar campanha<input type="search" value={campaignSearch} onChange={e => setCampaignSearch(e.target.value)} className="block w-full border rounded-md p-2 mt-1" placeholder="Nome da campanha" /></label>
            <div className="flex flex-wrap gap-2 my-3"><Button type="button" variant="outline" onClick={() => setCampaignChoices(prev => Object.fromEntries(Object.entries(prev).map(([id, choice]) => [id, {...choice, selected: true}])))}>Selecionar todas</Button><Button type="button" variant="outline" onClick={() => setCampaignChoices(prev => Object.fromEntries(Object.entries(prev).map(([id, choice]) => [id, {...choice, selected: false}])))}>Desmarcar todas</Button></div>
            <p>As ações acima incluem todas as campanhas, mesmo quando há busca ativa. {Object.values(campaignChoices).filter(c => c.selected).length} selecionadas.</p>
            {visibleCampaigns.length === 0 && <p>Nenhuma campanha encontrada.</p>}
            <div className="report-campaign-list">{visibleCampaigns.map(campaign => {
              const choice = campaignChoices[campaign.id] || {selected:false, metrics:[]};
              const selectedLabels = METRIC_OPTIONS.filter(([key]) => choice.metrics.includes(key)).map(([, label]) => label);
              return <div className="report-campaign-choice" key={campaign.id}><label className="report-campaign-toggle"><input type="checkbox" checked={choice.selected} onChange={e => setCampaignChoices(prev => ({...prev, [campaign.id]: {...choice, selected:e.target.checked}}))} /><strong>{campaign.name}</strong><span>{campaign.platform === 'meta_ads' ? 'Meta Ads' : 'Google Ads'}</span></label>
                {choice.selected ? <><p className="report-campaign-summary">{selectedLabels.length ? selectedLabels.join(' · ') : 'Escolha ao menos uma métrica para incluir esta campanha.'}</p><details className="report-campaign-details"><summary><span>{selectedLabels.length ? `${selectedLabels.length} ${selectedLabels.length === 1 ? 'métrica selecionada' : 'métricas selecionadas'}` : 'Nenhuma métrica selecionada'}</span><span className="report-campaign-action">Personalizar métricas</span></summary>
                  <div className="report-metric-options">{METRIC_OPTIONS.map(([key,label]) => <label key={key}><input type="checkbox" checked={choice.metrics.includes(key)} onChange={() => setCampaignChoices(prev => ({...prev, [campaign.id]: {...choice, metrics:toggleMetric(choice.metrics,key)}}))} />{label}</label>)}</div>
                </details></> : <p className="report-campaign-excluded">Fora deste relatório</p>}
              </div>;
            })}</div>
          </fieldset>}
          <label className="block text-slate-200">Análise da agência <span className="text-slate-400">(opcional)</span><textarea maxLength={3000} value={agencyAnalysis} onChange={e => setAgencyAnalysis(e.target.value)} rows={4} className="block w-full border rounded-md p-2 mt-1 bg-card" placeholder="Explique os resultados para o cliente" /></label>
          <label className="block text-slate-200">Próximos passos <span className="text-slate-400">(opcional)</span><textarea maxLength={3000} value={nextSteps} onChange={e => setNextSteps(e.target.value)} rows={3} className="block w-full border rounded-md p-2 mt-1 bg-card" placeholder="O que a agência pretende fazer a seguir" /></label>
          <section aria-label="Resumo antes de gerar" className="report-config-block"><h3 className="font-semibold">Confira antes de gerar</h3><p>Cliente: {clients.find(c => c.id === selectedClient)?.name || 'Selecione um cliente'} · Campanhas: {Object.values(campaignChoices).filter(c => c.selected).length}</p><p>Agência: {agencyName.trim() || 'não informada'} · Logo: {agencyLogo ? 'incluída' : 'não incluída'}</p><p>Período: últimos 30 dias de cada sincronização.</p><p>Texto da agência: {agencyAnalysis.trim() ? 'incluído' : 'não incluído'} · Próximos passos: {nextSteps.trim() ? 'incluídos' : 'não incluídos'}</p>{(preview?.campaigns || []).filter(c => campaignChoices[c.id]?.selected).map(c => <p key={c.id}>{c.name}: {METRIC_OPTIONS.filter(([key]) => campaignChoices[c.id].metrics.includes(key)).map(([,label]) => label).join(', ') || 'nenhuma métrica'}</p>)}</section>
          <p className="text-xs text-slate-400">Análise por IA para relatórios personalizados ficará disponível em uma próxima etapa.</p>
          {reportBlockedReason && <div id="report-blocked-reason" role="status" className="rounded-lg border border-amber-400/30 bg-amber-950/20 p-4 text-sm text-amber-100 space-y-3">
            <p>{reportBlockedReason}</p>
            {selectedClient && !loadingPreview && !preview && <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={() => navigate(`/clients/${encodeURIComponent(selectedClient)}`)}>Ver conexões do cliente</Button>
              <Button type="button" variant="outline" onClick={() => { const lab = document.getElementById('report-demo'); if (lab) {lab.open = true; lab.scrollIntoView({behavior: 'smooth'});} }}>Testar com dados fictícios</Button>
              <Button type="button" variant="outline" onClick={() => setRefresh(v => v + 1)}>Tentar carregar novamente</Button>
            </div>}
          </div>}
          <Button type="button" variant="outline" className="mr-2" disabled={busy || Boolean(reportBlockedReason)} onClick={e => create(e, true)}>Visualizar antes de salvar</Button>
          <Button type="submit" disabled={busy || Boolean(reportBlockedReason)} aria-describedby={reportBlockedReason ? 'report-blocked-reason' : undefined}>
            {busy ? 'Gerando relatório...' : 'Criar relatório'}
          </Button>
        </form>

        {draftPreview && <div className="space-y-2"><p className="text-sm text-blue-200">Prévia não salva. Se alterar os campos, gere a prévia novamente.</p><ReportDetail report={draftPreview} exporting={exporting} onClose={() => setDraftPreview(null)} onExport={async (id, print) => { try { await exportReport(id, print, draftPreview.rendered_html); } catch (err) { setError(err.message); } }} /></div>}
        {detailLoading && <p role="status">Abrindo relatório...</p>}
        {detail && <ReportDetail report={detail} exporting={exporting} onExport={download}
          onClose={() => setParams(selectedClient ? { client_id: selectedClient } : {})} />}
        <h2 className="text-xl font-semibold text-white">Histórico</h2>
        <div className="flex flex-wrap gap-4"><label className="text-slate-200">Buscar por título<input type="search" maxLength={200} value={historySearch} onChange={e => {setPage(0); setHistorySearch(e.target.value);}} placeholder="Título do relatório" className="block border rounded-md p-2 mt-1 bg-card" /></label><label className="text-slate-200">Criados a partir de<input type="date" value={dateFrom} onChange={e => {setPage(0); setDateFrom(e.target.value);}} className="block border rounded-md p-2 mt-1 bg-card" /></label><label className="text-slate-200">Criados até<input type="date" value={dateTo} onChange={e => {setPage(0); setDateTo(e.target.value);}} className="block border rounded-md p-2 mt-1 bg-card" /></label></div>
        <p className="text-xs text-slate-400">O cliente escolhido acima também filtra o histórico. As datas consideram o dia de criação em UTC.</p>
        {historyError ? <div role="alert" className="dash-panel p-4">{historyError} <Button variant="outline" onClick={() => setRefresh(v => v + 1)}>Tentar novamente</Button></div> : loading ? <p role="status">Carregando relatórios...</p> : reports.length === 0 ? <p className="text-slate-400">Nenhum relatório salvo nesta seleção.</p> :
          <div className="grid md:grid-cols-2 gap-4">{reports.map((report) => <ReportCard key={report.id} report={report}
            disabled={exporting || busy} onExport={download} onDuplicate={loadDuplicate} onDelete={() => removeReport(report)}
            onView={(id) => setParams({ ...(selectedClient ? { client_id: selectedClient } : {}), report_id: id })} />)}</div>}
        <div className="flex gap-2">
          <Button variant="outline" disabled={loading || page === 0} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
          <Button variant="outline" disabled={loading || reports.length < 20} onClick={() => setPage((p) => p + 1)}>Próxima</Button>
        </div>
        <details id="report-demo" className="dash-panel p-5"><summary className="cursor-pointer text-sm font-medium">Laboratório de relatórios · dados demonstrativos</summary><div className="mt-4"><DemoReport aiConfigured={ai?.configured} demoAIEnabled={ai?.demo_ai_enabled} /></div></details>
        <p className="text-xs text-slate-400">PDF: use “Imprimir / Salvar PDF” e escolha “Salvar como PDF” no navegador.</p>
      </div>
    </Layout></>
  );
}
