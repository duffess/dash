import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

const AccountSelectorModal = ({ isOpen, integrationId, onClose, onSelect }) => {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isOpen || !integrationId) return;
    let active = true;
    setLoading(true);
    setAccounts([]);
    api.get(`/integrations/${integrationId}/accounts`)
      .then(({ data }) => { if (active) setAccounts(data.accounts || []); })
      .catch((error) => {
        if (!active) return;
        toast({
          title: 'Erro ao buscar contas',
          description: error.response?.data?.detail || 'Não foi possível carregar as contas de anúncios.',
          variant: 'destructive',
        });
        onClose();
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isOpen, integrationId]);

  const handleSelectAccount = async (accountId) => {
    setSaving(true);
    try {
      await api.put(`/integrations/${integrationId}`, {
        account_id: accountId,
        status: 'connected',
      });
      toast({
        title: 'Conta Conectada!',
        description: `O ID ${accountId} foi vinculado com sucesso.`,
      });
      onSelect(accountId);
    } catch (error) {
      toast({
        title: 'Erro ao vincular',
        description: error.response?.data?.detail || 'Houve uma falha ao salvar sua conta.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-[#0B1326]/80 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[#131B2E] border border-slate-800 shadow-2xl p-6 z-50 overflow-hidden rounded-none"
          >
            {/* Architectural Border Highlight */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-[#2563EB]" />

            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 font-['Unbounded']">
                  Selecione a Conta
                </h2>
                <p className="text-slate-400 mt-1 font-['Space_Grotesk']">
                  Selecione a conta de anúncios deste cliente.
                </p>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-slate-800 transition-colors text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 text-[#2563EB] animate-spin mb-4" />
                <p className="text-slate-400 animate-pulse">Buscando contas de anúncios...</p>
              </div>
            ) : accounts.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-slate-300 mb-4">Nenhuma conta de anúncios encontrada vinculada a este e-mail.</p>
                <Button onClick={onClose} variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800">
                  Cancelar
                </Button>
              </div>
            ) : (
              <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
                {accounts.map((accountId) => (
                  <button
                    key={accountId}
                    onClick={() => handleSelectAccount(accountId)}
                    disabled={saving}
                    className="w-full flex items-center justify-between p-4 bg-[#171F33] border border-slate-800 hover:border-[#2563EB]/50 transition-all group disabled:opacity-50"
                  >
                    <div className="text-left">
                      <p className="font-['Space_Grotesk'] text-white font-medium flex items-center gap-2">
                        {accountId}
                      </p>
                      <p className="text-xs text-slate-500 mt-1 uppercase tracking-wider">ID da conta</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-[#2563EB] transform transition-transform group-hover:translate-x-1" />
                  </button>
                ))}
              </div>
            )}
            <style jsx>{`
              .custom-scrollbar::-webkit-scrollbar {
                width: 6px;
              }
              .custom-scrollbar::-webkit-scrollbar-track {
                background: #0B1326;
              }
              .custom-scrollbar::-webkit-scrollbar-thumb {
                background: #171F33;
              }
            `}</style>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default AccountSelectorModal;
