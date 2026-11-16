import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet';
import { useSearchParams } from 'react-router-dom';
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
  const selectedClient = params.get('client_id') || '';
  const reportId = params.get('report_id');
  const [clients, setClients] = useState([]);
  const [reports, setReports] = useState([]);
  const [detail, setDetail] = useState(null);
  const [title, setTitle] = useState('Relatório de campanhas');
  const [ai, setAI] = useState(null);
  const [preview, setPreview] = useState(null);
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
    Promise.all([api.get('/clients/'), api.get('/insights/status')]).then(([c, a]) => {
      if (active) { setClients(c.data); setAI(a.data); }
    }).catch(() => { if (active) setError('Não foi possível carregar clientes e configuração da IA.'); });
    return () => { active = false; };
  }, [refresh]);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setReports([]);
    api.get('/reports/', { params: { client_id: selectedClient || undefined, offset: page * 20, limit: 20 } })
      .then(({ data }) => { if (active) setReports(data); })
      .catch(() => { if (active) setError('Não foi possível carregar os relatórios.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selectedClient, page, refresh]);

  useEffect(() => {
    let active = true;
    setPreview(null); setPreviewMessage(''); setLoadingPreview(Boolean(selectedClient));
    if (!selectedClient) return () => { active = false; };
    api.get('/reports/preview', { params: { client_id: selectedClient } })
      .then(({ data }) => { if (active) setPreview(data); })
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

  const create = async (event) => {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      const campaignMetrics = Object.fromEntries(Object.entries(campaignChoices).filter(([, choice]) => choice.selected).map(([id, choice]) => [id, choice.metrics]));
      if (!Object.keys(campaignMetrics).length || Object.values(campaignMetrics).some(metrics => !metrics.length)) {
        setError('Selecione ao menos uma campanha e uma métrica para cada campanha escolhida.'); return;
      }
      const { data } = await api.post('/reports/', { client_id: selectedClient, title: title.trim(), include_ai: false, campaign_metrics: campaignMetrics });
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

  return (
    <><Helmet><title>Relatórios — DASH</title></Helmet><Layout>
      <div className="space-y-6">
        <div><h1 className="text-3xl font-bold text-white">Relatórios</h1><p className="text-slate-300 mt-1">Escolha campanhas e métricas para cada cliente.</p></div>
        {error && <div role="alert" className="border border-red-400/30 text-red-300 p-4 rounded-lg">{error} <Button variant="outline" onClick={() => setRefresh((v) => v + 1)}>Tentar novamente</Button></div>}
        <form onSubmit={create} className="dash-panel p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-100">Novo relatório</h2>
          <label className="block text-slate-200">Cliente
            <select aria-label="Cliente do relatório" value={selectedClient} disabled={busy}
              onChange={(e) => { setPage(0); setParams(e.target.value ? { client_id: e.target.value } : {}); }}
              className="block w-full border rounded-md p-2 mt-1 bg-card">
              <option value="">Todos os clientes — selecione um para criar</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </label>
          <label className="block text-slate-200">Título
            <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy}
              className="block w-full border rounded-md p-2 mt-1" />
          </label>
          <p className="text-sm text-slate-400">Período: últimos 30 dias de cada sincronização. Datas personalizadas estarão disponíveis quando houver histórico diário.</p>
          {loadingPreview && <p role="status">Consultando campanhas...</p>}
          {previewMessage && <p className="text-amber-200">{previewMessage}</p>}
          {preview && <p className="text-slate-300">{preview.campaigns.length} campanhas disponíveis para este cliente.</p>}
          <fieldset className="report-config-block"><legend>Seu padrão de métricas</legend><p>Escolha as métricas que serão selecionadas automaticamente para novas campanhas. Você pode ajustar cada campanha abaixo.</p>
            <div className="report-metric-options">{METRIC_OPTIONS.map(([key,label]) => <label key={key}><input type="checkbox" checked={metricChoice.includes(key)} onChange={() => setMetricChoice(values => toggleMetric(values,key))} />{label}</label>)}</div>
            <Button type="button" variant="outline" onClick={saveDefault}>Salvar padrão</Button> <span role="status" className="report-config-status">{defaultStatus}</span>
          </fieldset>
          {preview && <fieldset className="report-config-block"><legend>Campanhas e métricas</legend><p>Escolha as campanhas e personalize as métricas de cada uma. Métricas indisponíveis não serão inventadas no relatório.</p>
            <div className="report-campaign-list">{preview.campaigns.map(campaign => {
              const choice = campaignChoices[campaign.id] || {selected:false, metrics:[]};
              const selectedLabels = METRIC_OPTIONS.filter(([key]) => choice.metrics.includes(key)).map(([, label]) => label);
              return <div className="report-campaign-choice" key={campaign.id}><label className="report-campaign-toggle"><input type="checkbox" checked={choice.selected} onChange={e => setCampaignChoices(prev => ({...prev, [campaign.id]: {...choice, selected:e.target.checked}}))} /><strong>{campaign.name}</strong><span>{campaign.platform === 'meta_ads' ? 'Meta Ads' : 'Google Ads'}</span></label>
                {choice.selected ? <><p className="report-campaign-summary">{selectedLabels.length ? selectedLabels.join(' · ') : 'Escolha ao menos uma métrica para incluir esta campanha.'}</p><details className="report-campaign-details"><summary><span>{selectedLabels.length ? `${selectedLabels.length} ${selectedLabels.length === 1 ? 'métrica selecionada' : 'métricas selecionadas'}` : 'Nenhuma métrica selecionada'}</span><span className="report-campaign-action">Personalizar métricas</span></summary>
                  <div className="report-metric-options">{METRIC_OPTIONS.map(([key,label]) => <label key={key}><input type="checkbox" checked={choice.metrics.includes(key)} onChange={() => setCampaignChoices(prev => ({...prev, [campaign.id]: {...choice, metrics:toggleMetric(choice.metrics,key)}}))} />{label}</label>)}</div>
                </details></> : <p className="report-campaign-excluded">Fora deste relatório</p>}
              </div>;
            })}</div>
          </fieldset>}
          <p className="text-xs text-slate-400">Análise por IA para relatórios personalizados ficará disponível em uma próxima etapa.</p>
          <Button type="submit" disabled={busy || !preview || loadingPreview || !selectedClient || !title.trim()}>
            {busy ? 'Gerando relatório...' : 'Criar relatório'}
          </Button>
        </form>

        {detailLoading && <p role="status">Abrindo relatório...</p>}
        {detail && <ReportDetail report={detail} exporting={exporting} onExport={download}
          onClose={() => setParams(selectedClient ? { client_id: selectedClient } : {})} />}
        <h2 className="text-xl font-semibold text-white">Histórico</h2>
        {loading ? <p role="status">Carregando relatórios...</p> : reports.length === 0 ? <p className="text-slate-400">Nenhum relatório salvo nesta seleção.</p> :
          <div className="grid md:grid-cols-2 gap-4">{reports.map((report) => <ReportCard key={report.id} report={report}
            disabled={exporting || busy} onExport={download}
            onView={(id) => setParams({ ...(selectedClient ? { client_id: selectedClient } : {}), report_id: id })} />)}</div>}
        <div className="flex gap-2">
          <Button variant="outline" disabled={loading || page === 0} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
          <Button variant="outline" disabled={loading || reports.length < 20} onClick={() => setPage((p) => p + 1)}>Próxima</Button>
        </div>
        <details className="dash-panel p-5"><summary className="cursor-pointer text-sm font-medium">Laboratório de relatórios · dados demonstrativos</summary><div className="mt-4"><DemoReport aiConfigured={ai?.configured} demoAIEnabled={ai?.demo_ai_enabled} /></div></details>
        <p className="text-xs text-slate-400">PDF: use “Imprimir / Salvar PDF” e escolha “Salvar como PDF” no navegador.</p>
      </div>
    </Layout></>
  );
}
