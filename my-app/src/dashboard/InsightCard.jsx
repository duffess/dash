import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Loader2, Play } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

const InsightCard = () => {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const { toast } = useToast();

  const fetchInsights = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/insights/');
      if (data && data.length > 0) {
        setInsight(data[0]); // Pega o insight mais recente do user
      } else {
        setInsight(null);
      }
    } catch (error) {
      console.error('Erro ao buscar insights:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="architect-card p-8 flex flex-col h-[500px] bg-[#171F33] relative overflow-hidden group"
    >
      <div className="flex items-center justify-between mb-6 relative z-10">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 grad-dash flex items-center justify-center shadow-[0_0_20px_rgba(37,99,235,0.3)]">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-black text-white uppercase tracking-[0.2em]">CÉREBRO IA</h3>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Análise Executiva</p>
          </div>
        </div>
        {(loading || generating) && <Loader2 className="w-5 h-5 animate-spin text-[#2563EB]" />}
      </div>
      
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar relative z-10">
        {(loading || generating) ? (
          <div className="flex flex-col items-center justify-center h-full space-y-6 min-h-[250px]">
             <div className="relative">
               <div className="w-12 h-12 border-2 border-[#2563EB]/20 border-t-[#2563EB] animate-spin"></div>
             </div>
             <p className="text-[10px] text-[#2563EB] font-black uppercase tracking-[0.2em]">
               {generating ? 'Processando Modelos OpenAI...' : 'Carregando Cérebro...'}
             </p>
          </div>
        ) : insight ? (
          <motion.div 
             initial={{opacity: 0}} animate={{opacity: 1}}
             className="prose prose-invert prose-sm max-w-none 
                        prose-headings:text-white prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                        prose-strong:text-[#2563EB] prose-p:text-slate-300 prose-p:mb-4 prose-p:leading-relaxed 
                        prose-li:text-slate-300 prose-ul:mb-4"
          >
             <ReactMarkdown>{insight.content}</ReactMarkdown>
          </motion.div>
        ) : (
           <div className="flex flex-col items-center justify-center h-full text-center space-y-4 min-h-[250px]">
              <Sparkles className="w-12 h-12 text-slate-700" />
              <div>
                 <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Nenhum Relatório Gerado</p>
                 <p className="text-[10px] text-slate-500">Vá no painel de clientes e clique em "Gerar Análise IA" para ativar o Cérebro.</p>
              </div>
           </div>
        )}
      </div>

      <div className="mt-6 pt-6 border-t border-slate-800 relative z-10 bg-[#171F33]">
          <div className="flex items-center justify-between text-[10px] text-slate-600 font-black uppercase tracking-[0.2em]">
             <span>OpenAI GPT-4o Mini</span>
             <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 bg-[#2563EB] rounded-full animate-pulse"></div> Engine Ativa</span>
          </div>
      </div>
    </motion.div>
  );
};

export default InsightCard;
