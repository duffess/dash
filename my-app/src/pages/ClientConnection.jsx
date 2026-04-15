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
  const [showBrainModal, setShowBrainModal] = useState(false);

  useEffect(() => {
    if (pendingStatus === 'pending_account_select' && queryIntegrationId) {
      setShowAccountModal(true);
    }
  }, [pendingStatus, queryIntegrationId]);

  const statusMeta = useMemo(() => {
    const status = googleIntegration?.status;
    if (status === 'connected') {
      return { label: 'Conectado', className: 'bg-emerald-100 text-emerald-700' };
    }
    if (status === 'error') {
      return { label: 'Erro', className: 'bg-rose-100 text-rose-700' };
    }
    if (status === 'disconnected') {
      return { label: 'Desconectado', className: 'bg-slate-200 text-slate-700' };
    }
    if (status === 'pending_account_select') {
      return { label: 'Selecione a Conta', className: 'bg-[#2563EB]/20 text-[#2563EB] ring-1 ring-[#2563EB]/50' };
    }
    return { label: 'Nao conectado', className: 'bg-slate-100 text-slate-600' };
  }, [googleIntegration]);

  const statusMetaAdsBadge = useMemo(() => {
    const status = metaIntegration?.status;
    if (status === 'connected') {
      return { label: 'Conectado', className: 'bg-emerald-100 text-emerald-700' };
    }
    if (status === 'error') {
      return { label: 'Erro', className: 'bg-rose-100 text-rose-700' };
    }
    return { label: 'Nao conectado', className: 'bg-slate-100 text-slate-600' };
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
      setSyncing(false);
    }
  };

  const handleCreateMockIntegration = async (platform = 'google_ads') => {
    setSyncing(true);
    try {
      const integration = platform === 'google_ads' ? googleIntegration : metaIntegration;
      let integrationId = integration?.id;
      
      if (!integrationId) {
        const { data: newInteg } = await api.post('/integrations/', {
           client_id: clientId,
           platform: platform,
           access_token: 'mock_token',
           status: 'connected'
        });
        integrationId = newInteg.id;
      }
      const { data } = await api.post(`/integrations/${integrationId}/mock`);
      toast({ title: 'Dados de Teste Gerados', description: 'Campanhas realistas injetadas.' });
      await Promise.all([fetchIntegrations(), fetchCampaigns()]);
    } catch (error) {
      toast({ title: 'Erro', description: 'Falha ao criar mock. Tente novamente.', variant: 'destructive' });
    } finally {
      setSyncing(false);
    }
  };

  const handleGenerateInsights = async () => {
    if (campaigns.length === 0) {
      toast({ title: 'Atenção', description: 'Nenhuma campanha carregada para analisar.', variant: 'destructive' });
      return;
    }
    setSyncing(true);
    try {
      await api.post(`/insights/${clientId}/generate`);
      toast({ title: 'Análise Pronta', description: 'O Cérebro IA terminou o diagnóstico.' });
      setShowBrainModal(true);
    } catch (error) {
      toast({ title: 'Erro IA', description: error.response?.data?.detail || 'Falha ao processar.', variant: 'destructive' });
    } finally {
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
      // Por enquanto o mock lida com isso, ou sync fake.
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
            <p className="text-slate-600">Carregando cliente...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!client) {
    return (
      <Layout>
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
          <h2 className="text-xl font-semibold text-slate-900">Cliente nao encontrado</h2>
          <p className="text-slate-500 mt-2">Volte para a lista e selecione outro cliente.</p>
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
        <title>Conexao - {client.name} | DashFlow</title>
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
              <h1 className="text-3xl font-bold text-slate-900">{client.name}</h1>
              <p className="text-slate-600 mt-1">
                {client.company || 'Empresa nao informada'} {client.email ? `- ${client.email}` : ''}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Plug className="w-5 h-5 text-[#2563EB]" />
                <h2 className="text-lg font-semibold text-slate-900">Conexoes</h2>
              </div>

              <div className="flex items-center justify-between border border-slate-200 rounded-lg p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-900">Google Ads</p>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusMeta.className}`}>
                      {statusMeta.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500">
                    {googleIntegration
                      ? 'Conta conectada para este cliente'
                      : 'Conecte a conta do cliente'}
                  </p>
                  {googleIntegration?.account_id && (
                    <p className="text-xs text-slate-500 mt-1">Account ID: {googleIntegration.account_id}</p>
                  )}
                  {googleIntegration?.sync_error && (
                    <p className="text-xs text-rose-600 mt-1">Erro sync: {googleIntegration.sync_error}</p>
                  )}
                </div>
                
                <div className="flex gap-2">
                  <Button 
                    variant="ghost" 
                    onClick={() => handleCreateMockIntegration('google_ads')} 
                    disabled={syncing}
                    className="text-slate-400 hover:text-slate-600 text-xs px-2"
                    title="Preencher com dados de teste"
                  >
                    Gerar Teste
                  </Button>
                  
                  {(!googleIntegration || googleIntegration.status === 'disconnected') && (
                    <Button onClick={handleConnectGoogle} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      Conectar
                    </Button>
                  )}
                  {googleIntegration?.status === 'pending_account_select' && (
                    <Button onClick={() => setShowAccountModal(true)} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      Selecionar Conta
                    </Button>
                  )}
                  {googleIntegration?.status === 'connected' && (
                    <Button onClick={handleSyncGoogle} variant="outline" disabled={syncing}>
                      <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                      {syncing ? 'Sincronizando...' : 'Sincronizar'}
                    </Button>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between border border-slate-200 rounded-lg p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-900">Meta Ads</p>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusMetaAdsBadge.className}`}>
                      {statusMetaAdsBadge.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500">
                    {metaIntegration
                      ? 'Conta conectada para este cliente'
                      : 'Conecte a conta do cliente'}
                  </p>
                  {metaIntegration?.sync_error && (
                    <p className="text-xs text-rose-600 mt-1">Erro sync: {metaIntegration.sync_error}</p>
                  )}
                </div>
                
                <div className="flex gap-2">
                  <Button 
                    variant="ghost" 
                    onClick={() => handleCreateMockIntegration('meta_ads')} 
                    disabled={syncing}
                    className="text-slate-400 hover:text-slate-600 text-xs px-2"
                    title="Preencher com dados de teste"
                  >
                    Gerar Teste
                  </Button>
                  
                  {(!metaIntegration || metaIntegration.status === 'disconnected') && (
                    <Button onClick={handleConnectMeta} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                      Conectar
                    </Button>
                  )}
                  {metaIntegration?.status === 'connected' && (
                    <Button onClick={handleSyncMeta} variant="outline" disabled={syncing}>
                      <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                      {syncing ? 'Sincronizando...' : 'Sincronizar'}
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 flex flex-col h-full">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-[#2563EB]" />
                  <h2 className="text-lg font-semibold text-slate-900">Campanhas</h2>
                </div>
                {campaigns.length > 0 && (
                  <div className="flex items-center">
                    <Button 
                      onClick={handleGenerateInsights} 
                      disabled={syncing}
                      className="bg-slate-900 hover:bg-slate-800 text-white shadow shadow-blue-500/20"
                    >
                      <Sparkles className="w-4 h-4 mr-2 text-blue-400" />
                      Acionar Cérebro IA
                    </Button>
                    {/* Botão de apenas visualizar se já existir */}
                    <Button
                      onClick={() => setShowBrainModal(true)}
                      variant="outline"
                      className="ml-2 text-slate-500 hover:text-slate-700"
                      title="Ver Relatório Anterior"
                    >
                      Ver Relatório
                    </Button>
                  </div>
                )}
              </div>

              {sortedCampaigns.length === 0 ? (
                <div className="text-center py-10">
                  <Link2Off className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                  <p className="text-slate-500">Nenhuma campanha encontrada.</p>
                  <p className="text-sm text-slate-400 mt-1">
                    Conecte e sincronize para buscar campanhas deste cliente.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sortedCampaigns.map((campaign) => (
                    <div key={campaign.id} className="border border-slate-200 rounded-lg p-3">
                      <div className="flex justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-900">{campaign.name}</p>
                          <p className="text-xs text-slate-500">
                            {campaign.platform} | source: {campaign.source}
                          </p>
                        </div>
                        <span className="text-sm text-slate-700">{campaign.status}</span>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600">
                        <span>Spend: R$ {campaign.spend}</span>
                        <span>CTR: {campaign.ctr}%</span>
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
        integrationId={queryIntegrationId || googleIntegration?.id}
        onClose={() => setShowAccountModal(false)}
        onSelect={() => {
          setShowAccountModal(false);
          // O timeout é para dar tempo de limpar URL sem flicar
          setTimeout(() => {
            navigate(location.pathname, { replace: true });
            fetchIntegrations();
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
