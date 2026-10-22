import React, { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

export default function AIBrainModal({ isOpen, onClose, clientId }) {
  const navigate = useNavigate();
  const [insights, setInsights] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [ai, setAI] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [dataMessage, setDataMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const insight = insights.find((row) => row.id === selectedId);
  const hasMetrics = snapshot?.campaigns.some((c) => Object.values(c.metrics || {}).some((v) => typeof v === 'number' && v > 0));

  useEffect(() => {
    if (!isOpen || !clientId) return;
    let active = true;
    setLoading(true); setError(''); setInsights([]); setSelectedId(''); setAI(null); setSnapshot(null); setDataMessage('');
    Promise.allSettled([
      api.get(`/insights/${clientId}`), api.get('/insights/status'),
      api.get('/reports/preview', { params: { client_id: clientId } }),
    ]).then(([history, status, data]) => {
      if (!active) return;
      if (history.status === 'fulfilled') {
        setInsights(history.value.data); setSelectedId(history.value.data[0]?.id || '');
      } else setError('Não foi possível carregar o histórico de análises.');
      if (status.status === 'fulfilled') setAI(status.value.data);
      else setError('Não foi possível consultar a configuração da IA.');
      if (data.status === 'fulfilled') setSnapshot(data.value.data);
      else setDataMessage(data.reason.response?.data?.detail || 'Não foi possível consultar as campanhas.');
      setLoading(false);
    });
    return () => { active = false; };
  }, [isOpen, clientId, retry]);

  const generate = async () => {
    setBusy(true); setError('');
    try {
      const { data } = await api.post(`/insights/${clientId}/generate`);
      setInsights((rows) => [data, ...rows.filter((row) => row.id !== data.id)]); setSelectedId(data.id);
    } catch (err) { setError(err.response?.data?.detail || 'Falha ao gerar análise.'); }
    finally { setBusy(false); }
  };

  const saveReport = async () => {
    setBusy(true); setError('');
    try {
      const { data } = await api.post('/reports/', {
        client_id: clientId, insight_id: insight.id, title: `Análise de campanhas — ${insight.client_name}`,
      });
      onClose();
      navigate(`/reports?client_id=${clientId}&report_id=${data.id}`);
    } catch (err) { setError(err.response?.data?.detail || 'Falha ao salvar relatório.'); }
    finally { setBusy(false); }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70" />
        <Dialog.Content className="fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto bg-[#0B1326] border border-slate-700 rounded-xl p-6 space-y-5 text-slate-200">
          <div className="flex justify-between gap-3">
            <div><Dialog.Title className="text-xl font-bold">Cérebro IA</Dialog.Title>
              <Dialog.Description className="text-slate-400">Análise das campanhas do cliente · janela de 30 dias de cada sincronização.</Dialog.Description></div>
            <Button variant="outline" disabled={busy} onClick={onClose}>Fechar</Button>
          </div>
          {loading ? <p role="status">Carregando dados e histórico...</p> : <>
            {error && <div role="alert" className="text-red-300">{error} <Button variant="outline" disabled={busy} onClick={() => setRetry((v) => v + 1)}>Tentar novamente</Button></div>}
            {!ai?.configured && <p className="text-amber-300">IA não configurada. Defina OPENAI_API_KEY no backend e reinicie o servidor.</p>}
            {dataMessage && <p className="text-amber-300">{dataMessage}</p>}
            {snapshot && !hasMetrics && <p className="text-amber-300">Campanhas encontradas, mas ainda sem métricas para análise.</p>}
            {snapshot && <p className="text-xs text-slate-400">Indicadores disponíveis: {Object.values(snapshot.metric_definitions || {}).map((m) => m.label).join(', ') || 'nenhum'}. Campos ausentes não serão interpretados como zero.</p>}
            <p className="text-xs text-slate-400">Uma análise por cliente por dia (horário de Brasília), gerada ao clicar. Pedidos seguintes reutilizam a análise salva, inclusive nos relatórios, sem nova chamada à IA. A primeira geração envia métricas e nomes das campanhas à OpenAI e consome créditos. As recomendações não alteram anúncios.</p>
            <Button disabled={busy || !ai?.configured || !hasMetrics} onClick={generate}>{busy ? 'Processando...' : 'Obter análise do dia'}</Button>
            {insights.length > 0 ? <>
              <label className="block">Histórico de análises
                <select className="block w-full p-2 mt-1 bg-slate-800 border border-slate-600 rounded" value={selectedId}
                  disabled={busy} onChange={(e) => setSelectedId(e.target.value)}>
                  {insights.map((row) => <option key={row.id} value={row.id}>{new Date(row.created_at + (row.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR')} — {row.client_name}</option>)}
                </select>
              </label>
              {insight && <>
                <p className="text-sm text-slate-400">Gerada em {new Date(insight.created_at + (insight.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })} (Brasília).</p>
                <p className="text-sm text-slate-400">{insight.snapshot?.campaigns.length} campanhas · {insight.ai_model}</p>
                <div className="prose prose-invert max-w-none"><ReactMarkdown skipHtml components={{ img: () => null, a: ({ children }) => <span>{children}</span> }}>{insight.content}</ReactMarkdown></div>
                <p className="text-xs text-slate-400">Análise baseada nos dados salvos na geração; novas sincronizações não alteram este histórico.</p>
                <Button disabled={busy} onClick={saveReport}>Salvar como relatório</Button>
              </>}
            </> : <p className="text-slate-400">Nenhuma análise salva para este cliente.</p>}
          </>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
