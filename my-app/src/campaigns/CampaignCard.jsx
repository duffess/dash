import React from 'react';
import { motion } from 'framer-motion';
import { MoreVertical, TrendingUp, MousePointer, Target, DollarSign } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useToast } from '../components/ui/use-toast';

const CampaignCard = ({ campaign }) => {
  const { toast } = useToast();
  const budget = Number(campaign.budget) || 0;
  const spend = Number(campaign.spend ?? campaign.spent) || 0;
  const dailyBudget = Number(campaign.daily_budget) || 0;
  const budgetPercentage = budget > 0 ? (spend / budget) * 100 : 0;

  const handleViewDetails = () => {
    toast({
      title: "🚧 Funcionalidade em desenvolvimento",
      description: "A visualização detalhada de campanhas estará disponível em breve!",
    });
  };

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-slate-900">{campaign.name}</h3>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              campaign.status === 'active' 
                ? 'bg-[#2563EB]/10 text-[#2563EB]' 
                : 'bg-[#0F172A]/10 text-[#0F172A]'
            }`}>
              {({ active: 'Ativa', paused: 'Pausada', ended: 'Encerrada', archived: 'Arquivada', deleted: 'Excluída' })[campaign.status] || 'Desconhecido'}
            </span>
          </div>
          <p className="text-sm text-slate-500 mb-2">{campaign.client_name} · {campaign.platform === "meta_ads" ? "Meta Ads" : "Google Ads"}</p>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{budget > 0 ? `Orçamento total: R$ ${budget.toFixed(2)}` : dailyBudget > 0 ? `Orçamento diário: R$ ${dailyBudget.toFixed(2)}` : "Orçamento no conjunto de anúncios / indisponível"}</span>
            <span>•</span>
            <span>Gasto: R$ {spend.toFixed(2)}</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={handleViewDetails}>
          <MoreVertical className="w-5 h-5" />
        </Button>
      </div>

      {budget > 0 && <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-slate-600">Progresso do orçamento</span>
          <span className="font-medium text-slate-900">{budgetPercentage.toFixed(1)}%</span>
        </div>
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div 
            className="bg-[#2563EB] h-2 rounded-full transition-all"
            style={{ width: `${Math.min(budgetPercentage, 100)}%` }}
          />
        </div>
      </div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <MousePointer className="w-4 h-4 text-[#2563EB]" />
            <span className="text-xs text-slate-600">CTR</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">{campaign.ctr}%</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-4 h-4 text-[#0F172A]" />
            <span className="text-xs text-slate-600">CPC</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">R$ {campaign.cpc}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-4 h-4 text-[#0F172A]" />
            <span className="text-xs text-slate-600">Conversões</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">{campaign.conversions}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-[#2563EB]" />
            <span className="text-xs text-slate-600">Cliques</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">{campaign.clicks}</p>
        </div>
      </div>
    </motion.div>
  );
};

export default CampaignCard;
