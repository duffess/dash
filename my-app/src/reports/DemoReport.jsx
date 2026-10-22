import React, { useState } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import ReportDetail from './ReportDetail';
import { exportReport } from './exportReport';

export default function DemoReport({ aiConfigured, demoAIEnabled = false }) {
  const [scenario, setScenario] = useState('leads');
  const [includeAI, setIncludeAI] = useState(false);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const canUseAI = Boolean(aiConfigured && demoAIEnabled);
  const generate = async () => {
    setBusy(true); setError(''); setReport(null);
    try {
      const { data } = await api.post('/reports/demo', { scenario, include_ai: includeAI && canUseAI });
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
  return <section className="space-y-4 border border-blue-200 bg-blue-50 rounded-xl p-5">
    <div><h2 className="font-semibold text-blue-950 text-lg">Laboratório de relatórios + Cérebro IA</h2>
      <p className="text-sm text-blue-900 mt-1">Teste sem conectar anúncios. Dados fictícios, isolados dos seus clientes e do histórico real.</p></div>
    <label className="block text-sm text-slate-800">Cenário demonstrativo
      <select className="block w-full mt-1 rounded-md border p-2 bg-white" value={scenario} disabled={busy || exporting}
        onChange={(e) => { setScenario(e.target.value); setReport(null); }}>
        <option value="leads">Leads · CPL e comparação de períodos</option>
        <option value="sales">Vendas · receita, compras e ROAS</option>
        <option value="limited">Dados parciais · sem conversões ou receita</option>
        <option value="zero">Zero resultados · sem divisão por zero</option>
      </select>
    </label>
    <label className="flex gap-2 items-center text-sm text-slate-800">
      <input type="checkbox" checked={includeAI && canUseAI} disabled={!canUseAI || busy}
        onChange={(e) => setIncludeAI(e.target.checked)} /> Gerar análise real pela IA sobre os dados fictícios
    </label>
    <p className="text-xs text-slate-600">{canUseAI ? 'IA habilitada pelo administrador: essa opção consome créditos e não usa a cota diária por cliente.' : 'IA paga desativada no laboratório. Teste os relatórios de métricas gratuitamente, sem chamar o modelo.'}</p>
    <Button disabled={busy || exporting} onClick={generate}>{busy ? 'Preparando demonstração...' : 'Gerar demonstração'}</Button>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {report && <ReportDetail report={report} onClose={() => setReport(null)} onExport={download} exporting={exporting} />}
  </section>;
}
