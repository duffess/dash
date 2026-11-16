import React from 'react';
import { ArrowDownRight, ArrowRight, Target } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function CampaignSpotlight({ demo = false, loading = false }) {
  return <section className="dash-panel spotlight" aria-labelledby="spotlight-title" aria-busy={loading}>
    <div className="spotlight-top"><div className="spotlight-heading"><div><h2 id="spotlight-title">Destaque do dia</h2><p className="spotlight-eyebrow">Um olhar para o que importa</p></div></div>{demo && <span className="spotlight-demo">Prévia · dados fictícios</span>}</div>
    {loading ? <p className="spotlight-empty" role="status">Carregando campanhas…</p> : demo ? <>
      <div className="spotlight-content"><div className="spotlight-campaign"><div className="spotlight-context"><span>GERAÇÃO DE LEADS</span><span>·</span><span>META ADS</span></div><h3>Geração de leads</h3><p>Salão Aurora · cliente fictício</p><div className="spotlight-improvement"><ArrowDownRight size={16} aria-hidden="true" /><span><strong>18% menor</strong> custo por lead em relação ao período anterior</span></div></div>
        <div className="spotlight-stats"><div><span>Leads</span><strong>12</strong></div><div><span>Custo por lead</span><strong>R$ 8,50</strong></div></div></div>
      <div className="spotlight-footer"><span><Target size={15} aria-hidden="true" />Exemplo de escolha: melhora no custo por lead.</span><Link className="dash-link" to="/campaigns">Ver campanhas <ArrowRight size={15} aria-hidden="true" /></Link></div>
    </> : <div className="spotlight-placeholder"><p>{'Ainda não há dados diários suficientes para destacar uma campanha.'}</p><span>O destaque ficará disponível quando houver histórico para comparar.</span></div>}
  </section>;
}
