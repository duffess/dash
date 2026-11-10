import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import Layout from '@/components/Layout';
import api from '@/lib/api';
import MetricCard from '@/dashboard/MetricCard';
import PerformanceChart from '@/dashboard/PerformanceChart';
import InsightCard from '@/dashboard/InsightCard';
import CampaignCard from '@/campaigns/CampaignCard';
import { Button } from '@/components/ui/button';
import { BarChart3, MousePointer, Target, Wallet, CalendarDays, ArrowRight, Users, FileText, Megaphone } from 'lucide-react';
const number = (value) => Number.isFinite(value) ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : '—';
const money = (value) => Number.isFinite(value) ? value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [campaignError, setCampaignError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setCampaignError(''); setMetrics(null); setCampaigns([]);
    Promise.allSettled([api.get('/campaigns/summary', { params: { days: 30 } }), api.get('/campaigns/')]).then(([summary, list]) => {
      if (!active) return;
      if (summary.status === 'fulfilled') setMetrics(summary.value.data);
      else setError('Não foi possível carregar os indicadores. Tente novamente.');
      if (list.status === 'fulfilled') setCampaigns(list.value.data);
      else setCampaignError('Não foi possível carregar as campanhas.');
      setLoading(false);
    });
    return () => { active = false; };
  }, [retry]);
  const hasData = metrics?.campaign_count > 0;
  const value = (key, format = number) => hasData ? format(metrics[key]) : '—';
  return <><Helmet><title>Visão geral — DASH</title></Helmet><Layout>
    <div className="overview-heading"><div><span className="dash-kicker">SEU PANORAMA DE MÍDIA</span><h1>Visão geral</h1><p>Os resultados dos seus clientes, com espaço para enxergar o que importa.</p></div><span className="dash-chip"><CalendarDays size={16} aria-hidden="true" />Últimos 30 dias</span></div>
    {error && <div role="alert" className="dash-panel p-5 mb-5 text-red-200 flex flex-wrap items-center justify-between gap-3">{error}<Button variant="outline" onClick={() => setRetry(v => v + 1)}>Tentar novamente</Button></div>}
    <div className="overview-top">
      <section className="dash-panel agency-summary" aria-label="Resumo de resultados" aria-busy={loading}>
        <div className="agency-heading"><div className="agency-mark"><BarChart3 size={25} aria-hidden="true" /></div><div><h2>Resumo da agência</h2><p>{loading ? 'Carregando indicadores…' : error ? 'Indicadores indisponíveis' : hasData ? `${metrics.campaign_count} campanhas · Google Ads e Meta Ads` : 'Nenhuma campanha sincronizada'}</p></div></div>
        <div className="metric-grid">
          <MetricCard title="Investimento" value={value('total_spend', money)} icon={Wallet} />
          <MetricCard title="Conversões" value={value('total_conversions')} icon={Target} />
          <MetricCard title="CPC médio" value={value('avg_cpc', money)} icon={MousePointer} />
          <MetricCard title="CTR médio" value={hasData ? `${number(metrics.avg_ctr)}%` : '—'} icon={BarChart3} />
        </div>
        <div className="summary-footer"><span role="status">{loading ? 'Consultando dados…' : hasData ? 'Janela de 30 dias de cada sincronização' : error ? 'Confira sua conexão e tente novamente.' : 'Conecte uma conta na página do cliente.'}</span><Link className="dash-link" to={hasData ? '/reports' : '/clients'}>{hasData ? 'Ver relatórios' : 'Ver clientes'}<ArrowRight size={16} aria-hidden="true" /></Link></div>
      </section><InsightCard />
    </div>
    <section className="campaign-preview"><div className="panel-heading"><div><h2>Campanhas dos clientes</h2><p>Uma leitura rápida das campanhas sincronizadas.</p></div><Link to="/campaigns" className="dash-link">Ver todas<ArrowRight size={16} aria-hidden="true" /></Link></div>
      {loading ? <p role="status" className="text-slate-300">Carregando campanhas…</p> : campaignError ? <div role="alert" className="dash-panel p-5 text-red-200">{campaignError} <Button variant="outline" onClick={() => setRetry(v => v + 1)}>Tentar novamente</Button></div> : campaigns.length ? <div className="campaign-preview-grid">{campaigns.slice(0,3).map(c => <CampaignCard key={c.id} campaign={c} />)}</div> : <div className="dash-panel empty-state"><Megaphone aria-hidden="true" /><h3>Suas campanhas aparecerão aqui</h3><p>Escolha um cliente, conecte Google Ads ou Meta Ads e sincronize a conta para acompanhar os resultados.</p><Link to="/clients" className="dash-link">Abrir clientes<ArrowRight size={16} aria-hidden="true" /></Link></div>}
    </section>
    <div className="overview-bottom"><PerformanceChart /><section className="dash-panel workflow-panel"><div className="panel-heading"><div><h2>Seu próximo passo</h2><p>Da conexão ao relatório.</p></div></div>
      {[{to:'/clients',icon:Users,title:'Clientes e conexões',text:'Organize clientes e conecte as contas de anúncios.'},{to:'/campaigns',icon:Megaphone,title:'Acompanhar campanhas',text:'Consulte as métricas disponíveis por cliente.'},{to:'/reports',icon:FileText,title:'Preparar um relatório',text:'Reúna os dados salvos e revise os resultados.'}].map(({to,icon:Icon,title,text}) => <Link to={to} key={to} className="workflow-link"><Icon aria-hidden="true" /><div className="flex-1"><strong>{title}</strong><small>{text}</small></div><ArrowRight size={16} aria-hidden="true" /></Link>)}
    </section></div>

  </Layout></>;
}
