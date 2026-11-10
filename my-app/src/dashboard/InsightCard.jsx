import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';
import { Sparkles, ArrowRight } from 'lucide-react';

export default function InsightCard() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [ai, setAI] = useState(null);
  useEffect(() => {
    let active = true;
    Promise.all([api.get('/insights/'), api.get('/insights/status')])
      .then(([rows, status]) => { if (active) { setInsights(rows.data); setAI(status.data); } })
      .catch(() => { if (active) setError('Não foi possível carregar as análises.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const insight = insights[0];
  return <section className="dash-panel insight-panel">
    <div className="panel-heading"><div className="flex items-center gap-3"><span className="ai-symbol"><Sparkles size={21} aria-hidden="true" /></span><h2>Insight da IA</h2></div><span className="dash-kicker">DASH IA</span></div>
    <div className="insight-body">
      {loading ? <p role="status" className="text-slate-400">Carregando análises...</p> :
        error ? <p role="alert" className="text-red-300">{error}</p> :
        insight ? <>
          <p className="text-blue-400 text-sm mb-3">Última análise · {insight.client_name}</p>
          <div className="prose prose-invert prose-sm"><ReactMarkdown skipHtml components={{ img: () => null, a: ({ children }) => <span>{children}</span> }}>{insight.content}</ReactMarkdown></div>
          <Link className="text-blue-400 text-sm" to={`/clients/${insight.client_id}`}>Ver cliente e histórico →</Link>
        </> : <div className="py-4"><h3 className="text-lg text-white mb-3">Uma nova perspectiva sobre seus dados.</h3><p className="text-slate-300">Nenhuma análise salva. Acesse um cliente para consultar a disponibilidade da IA e analisar suas campanhas.</p><Link to="/clients" className="dash-link">Acessar clientes <ArrowRight size={16} aria-hidden="true" /></Link></div>}
    </div>
    <p className="insight-status">
      {ai ? (ai.configured ? 'IA disponível para análise nos clientes' : 'IA ainda não configurada') : 'Status da IA indisponível'}
    </p>
  </section>;
}
