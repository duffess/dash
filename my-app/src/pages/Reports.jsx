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

export default function Reports() {
  const [params, setParams] = useSearchParams();
  const selectedClient = params.get('client_id') || '';
  const reportId = params.get('report_id');
  const [clients, setClients] = useState([]);
  const [reports, setReports] = useState([]);
  const [detail, setDetail] = useState(null);
  const [title, setTitle] = useState('Relatório de campanhas');
  const [includeAI, setIncludeAI] = useState(false);
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
      const { data } = await api.post('/reports/', { client_id: selectedClient, title: title.trim(), include_ai: includeAI });
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
    <><Helmet><title>Relatórios - DashFlow</title></Helmet><Layout>
      <div className="space-y-6">
        <div><h1 className="text-3xl font-bold text-white">Relatórios</h1><p className="text-slate-300 mt-1">Métricas salvas por cliente, com análise IA opcional.</p></div>
        <DemoReport aiConfigured={ai?.configured} demoAIEnabled={ai?.demo_ai_enabled} />
        {error && <div role="alert" className="border border-red-200 text-red-700 p-4 rounded-lg">{error} <Button variant="outline" onClick={() => setRefresh((v) => v + 1)}>Tentar novamente</Button></div>}
        <form onSubmit={create} className="bg-white border rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900">Novo relatório</h2>
          <label className="block text-slate-700">Cliente
            <select aria-label="Cliente do relatório" value={selectedClient} disabled={busy}
              onChange={(e) => { setPage(0); setParams(e.target.value ? { client_id: e.target.value } : {}); }}
              className="block w-full border rounded-md p-2 mt-1 bg-white">
              <option value="">Todos os clientes — selecione um para criar</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </label>
          <label className="block text-slate-700">Título
            <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy}
              className="block w-full border rounded-md p-2 mt-1" />
          </label>
          <p className="text-sm text-slate-500">Período: últimos 30 dias de cada sincronização. Datas personalizadas estarão disponíveis quando houver histórico diário.</p>
          {loadingPreview && <p role="status">Consultando campanhas...</p>}
          {previewMessage && <p className="text-amber-700">{previewMessage}</p>}
          {preview && <p className="text-slate-600">{preview.campaigns.length} campanhas disponíveis para este cliente.</p>}
          <label className="flex gap-2 items-center text-slate-700">
            <input type="checkbox" checked={includeAI} disabled={busy || !ai?.configured}
              onChange={(e) => setIncludeAI(e.target.checked)} /> Incluir nova análise IA
          </label>
          <p className="text-xs text-slate-500">{ai?.configured ? 'Ao incluir IA, as métricas e nomes das campanhas serão enviados à OpenAI. A chamada consome créditos da API.' : 'IA indisponível: configure OPENAI_API_KEY no backend. Relatórios de métricas não dependem dessa chave.'}</p>
          <Button type="submit" disabled={busy || !preview || loadingPreview || !selectedClient || !title.trim()}>
            {busy ? 'Gerando relatório...' : 'Criar relatório'}
          </Button>
        </form>

        {detailLoading && <p role="status">Abrindo relatório...</p>}
        {detail && <ReportDetail report={detail} exporting={exporting} onExport={download}
          onClose={() => setParams(selectedClient ? { client_id: selectedClient } : {})} />}
        <h2 className="text-xl font-semibold text-white">Histórico</h2>
        {loading ? <p role="status">Carregando relatórios...</p> : reports.length === 0 ? <p className="text-slate-500">Nenhum relatório salvo nesta seleção.</p> :
          <div className="grid md:grid-cols-2 gap-4">{reports.map((report) => <ReportCard key={report.id} report={report}
            disabled={exporting || busy} onExport={download}
            onView={(id) => setParams({ ...(selectedClient ? { client_id: selectedClient } : {}), report_id: id })} />)}</div>}
        <div className="flex gap-2">
          <Button variant="outline" disabled={loading || page === 0} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
          <Button variant="outline" disabled={loading || reports.length < 20} onClick={() => setPage((p) => p + 1)}>Próxima</Button>
        </div>
        <p className="text-xs text-slate-500">PDF: use “Imprimir / Salvar PDF” e escolha “Salvar como PDF” no navegador.</p>
      </div>
    </Layout></>
  );
}
