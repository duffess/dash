import React, { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { ChevronRight, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

const AccountSelectorModal = ({ isOpen, integrationId, onClose, onSelect }) => {
  const { toast } = useToast();
  const openerRef = useRef(null);
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

  return <Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open && !saving) onClose(); }}><Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50" />
    <Dialog.Content onOpenAutoFocus={() => { openerRef.current = document.activeElement; }} onCloseAutoFocus={(event) => { event.preventDefault(); openerRef.current?.focus(); }} className="dash-dialog fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-32px)] max-w-lg max-h-[85dvh] overflow-y-auto p-6 z-50" onEscapeKeyDown={(event) => { if (saving) event.preventDefault(); }} onPointerDownOutside={(event) => { if (saving) event.preventDefault(); }}>
      <div className="flex justify-between items-start gap-4 mb-6"><div><Dialog.Title className="text-xl font-semibold text-white">Selecione a conta</Dialog.Title><Dialog.Description className="text-slate-300 mt-2">Selecione a conta de anúncios deste cliente.</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="icon" disabled={saving} aria-label="Fechar seleção de conta"><X size={20} /></Button></Dialog.Close></div>
            {loading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 text-blue-300 animate-spin mb-4" />
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
                    className="w-full flex items-center justify-between p-4 dash-inset border hover:border-[#2563EB]/50 transition-all group disabled:opacity-50"
                  >
                    <div className="text-left">
                      <p className="text-white font-medium flex items-center gap-2">
                        {accountId}
                      </p>
                      <p className="text-xs text-slate-300 mt-1 uppercase tracking-wider">ID da conta</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-300 transform transition-transform group-hover:translate-x-1" />
                  </button>
                ))}
              </div>
            )}
    </Dialog.Content></Dialog.Portal></Dialog.Root>;
};
export default AccountSelectorModal;
