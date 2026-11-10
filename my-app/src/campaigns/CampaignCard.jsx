import React from 'react';
import { motion } from 'framer-motion';
import { MoreVertical, TrendingUp, MousePointer, Target, Wallet } from 'lucide-react';
import { Button } from '../components/ui/button';

const num = (value) => Number.isFinite(Number(value)) ? Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : '—';
const brl = (value) => Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const CampaignCard = ({ campaign }) => {
  const budget = Number(campaign.budget) || 0;
  const spend = Number(campaign.spend ?? campaign.spent) || 0;
  const dailyBudget = Number(campaign.daily_budget) || 0;
  const budgetPercentage = budget > 0 ? (spend / budget) * 100 : 0;


  return (
    <motion.div

      className="dash-panel campaign-card p-6 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-slate-100">{campaign.name}</h3>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              campaign.status === 'active'
                ? 'bg-[#2563EB]/10 text-blue-300'
                : 'bg-secondary/70 text-slate-100'
            }`}>
              {({ active: 'Ativa', paused: 'Pausada', ended: 'Encerrada', archived: 'Arquivada', deleted: 'Excluída' })[campaign.status] || 'Desconhecido'}
            </span>
          </div>
          <p className="text-sm text-slate-400 mb-2">{campaign.client_name} · {campaign.platform === "meta_ads" ? "Meta Ads" : "Google Ads"}</p>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
            <span>{budget > 0 ? `Orçamento total: ${brl(budget)}` : dailyBudget > 0 ? `Orçamento diário: ${brl(dailyBudget)}` : "Orçamento no conjunto de anúncios / indisponível"}</span>
            <span>•</span>
            <span>Gasto: {brl(spend)}</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" disabled aria-label="Detalhes da campanha ainda indisponíveis" title="Detalhes em breve">
          <MoreVertical className="w-5 h-5" />
        </Button>
      </div>

      {budget > 0 && <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-slate-300">Progresso do orçamento</span>
          <span className="font-medium text-slate-100">{num(budgetPercentage)}%</span>
        </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
            className="bg-[#2563EB] h-2 rounded-full transition-all"
            style={{ width: `${Math.min(budgetPercentage, 100)}%` }}
          />
        </div>
      </div>}

      <div className="campaign-metrics grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-secondary/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <MousePointer className="w-4 h-4 text-blue-300" />
            <span className="text-xs text-slate-300">CTR</span>
          </div>
          <p className="text-lg font-semibold text-slate-100">{num(campaign.ctr)}%</p>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="w-4 h-4 text-slate-100" />
            <span className="text-xs text-slate-300">CPC</span>
          </div>
          <p className="text-lg font-semibold text-slate-100">{brl(campaign.cpc)}</p>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-4 h-4 text-slate-100" />
            <span className="text-xs text-slate-300">Conversões</span>
          </div>
          <p className="text-lg font-semibold text-slate-100">{num(campaign.conversions)}</p>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-blue-300" />
            <span className="text-xs text-slate-300">Cliques</span>
          </div>
          <p className="text-lg font-semibold text-slate-100">{num(campaign.clicks)}</p>
        </div>
      </div>
    </motion.div>
  );
};

export default CampaignCard;
