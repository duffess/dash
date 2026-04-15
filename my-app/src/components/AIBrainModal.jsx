import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, AlertCircle, FileText, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';

const AIBrainModal = ({ isOpen, onClose, clientId }) => {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isOpen || !clientId) return;
    
    const fetchLatestInsight = async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/insights/${clientId}`);
        if (data && data.length > 0) {
          setInsight(data[0]);
        } else {
          setInsight(null);
        }
      } catch (error) {
        console.error('Erro ao buscar insight avulso', error);
      } finally {
        setLoading(false);
      }
    };

    fetchLatestInsight();
  }, [isOpen, clientId]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="relative w-full max-w-4xl max-h-[90vh] bg-[#0B1326] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-[#0F172A]">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-[#2563EB]" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white uppercase tracking-wider">Consultoria IA</h2>
                <p className="text-sm text-slate-400">Análise Estratégica Executiva do Cliente</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content Body */}
          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-[#2563EB]/5 rounded-full blur-3xl pointer-events-none"></div>
            
            {loading ? (
              <div className="flex flex-col items-center justify-center h-64 space-y-4">
                <div className="w-12 h-12 border-4 border-[#2563EB]/20 border-t-[#2563EB] rounded-full animate-spin"></div>
                <p className="text-slate-400 font-medium">Lendo a mente da inteligência...</p>
              </div>
            ) : insight ? (
              <div className="prose prose-invert prose-lg max-w-none 
                              prose-headings:text-white prose-headings:font-black prose-headings:uppercase prose-headings:tracking-wider 
                              prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-headings:mt-8
                              prose-p:text-slate-300 prose-p:leading-loose prose-p:mb-8
                              prose-li:text-slate-300 prose-li:mb-8 prose-li:leading-relaxed
                              prose-strong:text-[#2563EB]">
                <ReactMarkdown>{insight.content}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
                <AlertCircle className="w-12 h-12 text-slate-600" />
                <div>
                  <p className="text-slate-300 font-bold text-lg">Nenhum relatório encontrado</p>
                  <p className="text-slate-500 mt-1">Acione o Cérebro IA no painel do cliente para gerar o primeiro diagnóstico.</p>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-6 border-t border-slate-800 bg-[#0F172A] flex justify-between items-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Engine Analítica OpenAI
            </span>
            <button 
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-medium transition-colors"
              onClick={() => alert("Função de PDF será implementada na v2")}
            >
              <Download className="w-4 h-4" />
              Exportar
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default AIBrainModal;
