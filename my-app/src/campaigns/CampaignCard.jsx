import React from 'react';
import { motion } from 'framer-motion';
import { Clock3, Info } from 'lucide-react';

const isNumber = value => typeof value === 'number' && Number.isFinite(value);
const num = value => isNumber(value) ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : '—';
const brl = value => isNumber(value) ? value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
const when = value => {
  if (!value) return null;
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

export default function CampaignCard({ campaign }) {
  const raw = campaign.report_metrics || {};
  const has = key => isNumber(raw[key]);
  const spend = has('spend') ? raw.spend : null;
  const impressions = has('impressions') ? raw.impressions : null;
  const clicks = has('clicks') ? raw.clicks : null;
  const demo = campaign.source === 'mock';
  const metaResults = campaign.platform === 'meta_ads';
  const conversions = metaResults ? (has('leads') || has('purchases') ? (raw.leads || 0) + (raw.purchases || 0) : null) : (has('conversions') ? raw.conversions : null);
  const metrics = [
    ['Investimento', brl(spend)], ['Impressões', num(impressions)], ['Cliques', num(clicks)],
    ['CTR', impressions > 0 && clicks !== null ? `${num(clicks / impressions * 100)}%` : '—'],
    ['CPC', clicks > 0 && spend !== null ? brl(spend / clicks) : '—'],
    ['CPM', impressions > 0 && spend !== null ? brl(spend / impressions * 1000) : '—'],
    [metaResults ? 'Leads + compras' : 'Conversões', num(conversions)],
  ];
  const sync = when(campaign.last_synced_at);
  return <motion.article className="dash-panel campaign-card p-6">
    <div className="campaign-card-header">
      <div className="min-w-0"><div className="campaign-title-row"><h3 className="text-lg font-semibold text-slate-100">{campaign.name}</h3><span className="campaign-status">{({active:'Ativa', paused:'Pausada', ended:'Encerrada', archived:'Arquivada', deleted:'Excluída'})[campaign.status] || 'Desconhecido'}</span>{demo && <span className="campaign-demo">Dado fictício</span>}</div>
        <p className="text-sm text-slate-400 mt-2">{campaign.client_name} · {metaResults ? 'Meta Ads' : 'Google Ads'}</p>
      </div>
      <span className="campaign-sync"><Clock3 size={14} aria-hidden="true" />{demo ? 'Exemplo local' : sync ? `Sincronizada em ${sync}` : 'Sincronização indisponível'}</span>
    </div>
    <div className="campaign-metrics campaign-metrics-expanded">{metrics.map(([label, value]) => <div key={label} className="campaign-metric-tile"><span>{label}</span><strong>{value}</strong></div>)}</div>
    <p className="campaign-metric-note"><Info size={14} aria-hidden="true" />{metaResults ? 'Na Meta, este total reúne leads e compras disponíveis; não equivale necessariamente às conversões do Google.' : 'Métricas do último período sincronizado. — indica dado indisponível ou cálculo sem base.'}</p>
  </motion.article>;
}
