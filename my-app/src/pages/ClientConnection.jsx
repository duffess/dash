import React, { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Plug, ChevronLeft, Link2Off, Megaphone, RefreshCw, Sparkles } from 'lucide-react';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';
import AccountSelectorModal from '@/components/AccountSelectorModal';
import AIBrainModal from '@/components/AIBrainModal';

const ClientConnection = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [client, setClient] = useState(null);
  const [googleIntegration, setGoogleIntegration] = useState(null);
  const [metaIntegration, setMetaIntegration] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Modal Control
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const pendingStatus = searchParams.get('status');
  const queryIntegrationId = searchParams.get('integration_id');
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [selectedIntegrationId, setSelectedIntegrationId] = useState(null);
  const openAccountSelector = (id) => { setSelectedIntegrationId(id); setShowAccountModal(true); };
  const [showBrainModal, setShowBrainModal] = useState(false);

  useEffect(() => {
    if (pendingStatus === 'pending_account_select' && queryIntegrationId) {
      openAccountSelector(queryIntegrationId);
    }
  }, [pendingStatus, queryIntegrationId]);

  const statusMeta = useMemo(() => {
    const status = googleIntegration?.status;
    if (status === 'connected') {
      return { label: 'Conectado', className: 'bg-emerald-950 text-emerald-200' };
    }
    if (status === 'error') {
      return { label: 'Erro', className: 'bg-rose-950 text-rose-200' };
    }
    if (status === 'disconnected') {
      return { label: 'Desconectado', className: 'bg-secondary text-slate-200' };
    }
    if (status === 'pending_account_select') {
      return { label: 'Selecione a Conta', className: 'bg-[#2563EB]/20 text-blue-300 ring-1 ring-[#2563EB]/50' };
    }
    return { label: 'Não conectado', className: 'bg-secondary text-slate-300' };
  }, [googleIntegration]);

  const statusMetaAdsBadge = useMemo(() => {
    const status = metaIntegration?.status;
    if (status === 'pending_account_select' || (status === 'connected' && !metaIntegration?.account_id)) {
      return { label: 'Selecione a Conta', className: 'bg-blue-950 text-blue-200' };
    }
    if (status === 'connected') {
      return { label: 'Conectado', className: 'bg-emerald-950 text-emerald-200' };
    }
    if (status === 'error') {
      return { label: 'Erro', className: 'bg-rose-950 text-rose-200' };
    }
    return { label: 'Não conectado', className: 'bg-secondary text-slate-300' };
  }, [metaIntegration]);

  const sortedCampaigns = useMemo(
    () => [...campaigns].sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || '')),
    [campaigns],
  );

  const fetchClient = async () => {
    const { data } = await api.get(`/clients/${clientId}`);
    setClient(data);
  };

  const fetchIntegrations = async () => {
    const { data } = await api.get('/integrations/');
    const googleRow = data.find((item) => item.client_id === clientId && item.platform === 'google_ads');
    const metaRow = data.find((item) => item.client_id === clientId && item.platform === 'meta_ads');
    setGoogleIntegration(googleRow || null);
    setMetaIntegration(metaRow || null);
  };

  const fetchCampaigns = async () => {
    const { data } = await api.get('/campaigns/', { params: { client_id: clientId } });
    setCampaigns(data || []);
  };

  useEffect(() => {
    const boot = async () => {
      try {
        await Promise.all([fetchClient(), fetchIntegrations(), fetchCampaigns()]);
      } catch (error) {
        toast({
          title: 'Erro ao carregar dados',
          description: error.response?.data?.detail || 'Verifique o cliente e tente novamente.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };
    if (clientId) {
      boot();
    }
  }, [clientId, toast]);

  const handleConnectGoogle = async () => {
    if (!clientId) return;
    try {
      const { data } = await api.get('/auth/google/connect', { params: { client_id: clientId } });
      if (!data?.auth_url) throw new Error('URL de autenticacao nao recebida');
      window.location.href = data.auth_url;
    } catch (error) {
      toast({
        title: 'Erro ao iniciar conexao',
        description: error.response?.data?.detail || error.message || 'Nao foi possivel iniciar OAuth do Google.',
        variant: 'destructive',
      });
    }
  };

  const handleSyncGoogle = async () => {
    if (!googleIntegration?.id) return;
    setSyncing(true);
    try {
      const { data } = await api.post(`/integrations/${googleIntegration.id}/sync`);
      toast({
        title: 'Sincronizacao concluida',
        description: `${data.synced_campaigns} campanhas sincronizadas.`,
      });
      await Promise.all([fetchIntegrations(), fetchCampaigns()]);
    } catch (error) {
      toast({
        title: 'Erro ao sincronizar',
        description: error.response?.data?.detail || 'Falha durante sincronizacao.',
        variant: 'destructive',
      });
    } finally {
      await fetchIntegrations().catch(() => {});
      setSyncing(false);
    }
  };

  const handleConnectMeta = async () => {
    if (!clientId) return;
    try {
      const { data } = await api.get('/auth/meta/connect', { params: { client_id: clientId } });
      if (!data?.auth_url) throw new Error('URL de autenticacao nao recebida');
      window.location.href = data.auth_url;
    } catch (error) {
      toast({
        title: 'Erro ao iniciar conexao Meta',
        description: error.response?.data?.detail || error.message || 'Falha no OAuth do Meta.',
        variant: 'destructive',
      });
    }
  };

  const handleSyncMeta = async () => {
    if (!metaIntegration?.id) return;
    setSyncing(true);
    try {
      const { data } = await api.post(`/integrations/${metaIntegration.id}/sync`);
      toast({
        title: 'Sincronizacao concluida',
        description: `${data.synced_campaigns} campanhas Meta sincronizadas.`,
      });
      await Promise.all([fetchIntegrations(), fetchCampaigns()]);
    } catch (error) {
      toast({
        title: 'Erro ao sincronizar',
        description: error.response?.data?.detail || 'Falha durante sincronizacao Meta.',
        variant: 'destructive',
      });
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-300">Carregando cliente...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!client) {
    return (
      <Layout>
        <div className="dash-panel p-8 text-center">
          <h2 className="text-xl font-semibold text-slate-100">Cliente não encontrado</h2>
          <p className="text-slate-400 mt-2">Volte para a lista e selecione outro cliente.</p>
          <Button className="mt-4" onClick={() => navigate('/clients')}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Voltar para clientes
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <>
      <Helmet>
        <title>Conexões — {client.name} | DASH</title>
        <meta name="description" content="Gerencie conexoes e campanhas do cliente" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <Button variant="ghost" onClick={() => navigate('/clients')} className="mb-3">
                <ChevronLeft className="w-4 h-4 mr-2" />
                Voltar para clientes
              </Button>
              <h1 className="text-3xl font-bold text-slate-100">{client.name}</h1>
              <p className="text-slate-300 mt-1">
                {client.company || 'Empresa nao informada'} {client.email ? `- ${client.email}` : ''}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="dash-panel p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Plug className="w-5 h-5 text-blue-300" />
                <h2 className="text-lg font-semibold text-slate-100">Conexões</h2>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 border border-border rounded-lg p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-100">Google Ads</p>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusMeta.className}`}>
                      {statusMeta.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">
                    {googleIntegration
                      ? 'Conta conectada para este cliente'
                      : 'Conecte a conta do cliente'}
                  </p>
                  {googleIntegration?.account_id && (
                    <p className="text-xs text-slate-400 mt-1">Account ID: {googleIntegration.account_id}</p>
                  )}
                  {googleIntegration?.sync_error && (
                    <p className="text-xs text-rose-300 mt-1">Erro sync: {googleIntegration.sync_error}</p>
                  )}
                </div>
                
                <div className="flex flex-wrap gap-2">
                  {(
                    <Button onClick={handleConnectGoogle} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      {googleIntegration ? 'Reconectar' : 'Conectar'}
                    </Button>
                  )}
                  {googleIntegration && (googleIntegration.status === 'pending_account_select' || !googleIntegration.account_id) && (
                    <Button onClick={() => openAccountSelector(googleIntegration.id)} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      Selecionar Conta
                    </Button>
                  )}
                  {['connected', 'error'].includes(googleIntegration?.status) && googleIntegration?.account_id && (
                    <Button onClick={handleSyncGoogle} variant="outline" disabled={syncing}>
                      <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                      {syncing ? 'Sincronizando...' : 'Sincronizar'}
                    </Button>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 border border-border rounded-lg p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-100">Meta Ads</p>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusMetaAdsBadge.className}`}>
                      {statusMetaAdsBadge.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">
                    {metaIntegration
                      ? 'Conta conectada para este cliente'
                      : 'Conecte a conta do cliente'}
                  </p>
                  {metaIntegration?.account_id && <p className="text-xs text-slate-400 mt-1">Conta: {metaIntegration.account_id}</p>}
                  {metaIntegration?.sync_error && (
                    <p className="text-xs text-rose-300 mt-1">Erro sync: {metaIntegration.sync_error}</p>
                  )}
                </div>
                
                <div className="flex flex-wrap gap-2">
                  {(
                    <Button onClick={handleConnectMeta} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      {metaIntegration ? 'Reconectar' : 'Conectar'}
                    </Button>
                  )}
                  {metaIntegration && (metaIntegration.status === 'pending_account_select' || !metaIntegration.account_id) && (
                    <Button onClick={() => openAccountSelector(metaIntegration.id)}>Selecionar Conta</Button>
                  )}
                  {['connected', 'error'].includes(metaIntegration?.status) && metaIntegration?.account_id && (
                    <Button onClick={handleSyncMeta} variant="outline" disabled={syncing}>
                      <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                      {syncing ? 'Sincronizando...' : 'Sincronizar'}
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <div className="dash-panel p-6 space-y-4 flex flex-col h-full">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-blue-300" />
                  <h2 className="text-lg font-semibold text-slate-100">Campanhas</h2>
                </div>
                {(
                  <div className="flex items-center">
                    <Button 
                      onClick={() => setShowBrainModal(true)}
                      disabled={syncing}
                      className="bg-slate-900 hover:bg-slate-800 text-white shadow shadow-blue-500/20"
                    >
                      <Sparkles className="w-4 h-4 mr-2 text-blue-400" />
                      Abrir Cérebro IA
                    </Button>

                  </div>
                )}
              </div>

              {sortedCampaigns.length === 0 ? (
                <div className="text-center py-10">
                  <Link2Off className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                  <p className="text-slate-400">Nenhuma campanha encontrada.</p>
                  <p className="text-sm text-slate-400 mt-1">
                    Conecte e sincronize para buscar campanhas deste cliente.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sortedCampaigns.map((campaign) => (
                    <div key={campaign.id} className="border border-border rounded-lg p-3">
                      <div className="flex justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-100">{campaign.name}</p>
                          <p className="text-xs text-slate-400">
                            {campaign.platform === 'meta_ads' ? 'Meta Ads' : 'Google Ads'}
                          </p>
                        </div>
                        <span className="text-sm text-slate-200">{({active: 'Ativa', paused: 'Pausada', ended: 'Encerrada', archived: 'Arquivada', deleted: 'Excluída'})[campaign.status] || 'Desconhecido'}</span>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-300">
                        <span>Gasto: {Number(campaign.spend).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
                        <span>CTR: {Number(campaign.ctr).toLocaleString('pt-BR')}%</span>
                        <span>Conv: {campaign.conversions}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </Layout>

      <AccountSelectorModal
        isOpen={showAccountModal}
        integrationId={selectedIntegrationId}
        onClose={() => setShowAccountModal(false)}
        onSelect={() => {
          setShowAccountModal(false);
          // O timeout é para dar tempo de limpar URL sem flicar
          setTimeout(() => {
            navigate(location.pathname, { replace: true });
            fetchIntegrations();
            fetchCampaigns();
          }, 300);
        }}
      />
      <AIBrainModal
        isOpen={showBrainModal}
        onClose={() => setShowBrainModal(false)}
        clientId={clientId}
      />
    </>
  );
};

export default ClientConnection;
