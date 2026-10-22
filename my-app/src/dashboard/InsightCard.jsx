import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';

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
  return <section className="architect-card bg-[#171F33] p-8 h-[500px] flex flex-col">
    <h3 className="text-sm font-black text-white uppercase tracking-widest mb-4">Cérebro IA</h3>
    <div className="flex-1 overflow-y-auto">
      {loading ? <p role="status" className="text-slate-400">Carregando análises...</p> :
        error ? <p role="alert" className="text-red-300">{error}</p> :
        insight ? <>
          <p className="text-blue-400 text-sm mb-3">Última análise · {insight.client_name}</p>
          <div className="prose prose-invert prose-sm"><ReactMarkdown skipHtml components={{ img: () => null, a: ({ children }) => <span>{children}</span> }}>{insight.content}</ReactMarkdown></div>
          <Link className="text-blue-400 text-sm" to={`/clients/${insight.client_id}`}>Ver cliente e histórico →</Link>
        </> : <p className="text-slate-400">Nenhuma análise salva. Abra um cliente e acesse o Cérebro IA.</p>}
    </div>
    <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-700">
      {ai ? (ai.configured ? `OpenAI · ${ai.model} · configurada` : 'IA aguardando configuração no backend') : 'Status da IA indisponível'}
    </p>
  </section>;
}
