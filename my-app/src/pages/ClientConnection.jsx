import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet';
import { useNavigate, useParams } from 'react-router-dom';
import { Plug, ChevronLeft, Link2Off, Megaphone } from 'lucide-react';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

const ClientConnection = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchClient = async () => {
      try {
        const { data } = await api.get(`/clients/${clientId}`);
        setClient(data);
      } catch (error) {
        toast({
          title: 'Cliente nÃ£o encontrado',
          description: 'Verifique se o cliente existe e tente novamente.',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    if (clientId) {
      fetchClient();
    }
  }, [clientId, toast]);

  const handleConnectGoogle = () => {
    toast({
      title: 'ConexÃ£o em desenvolvimento',
      description: 'Aqui entraremos com o OAuth do Google Ads para este cliente.',
    });
  };

  const handleConnectMeta = () => {
    toast({
      title: 'ConexÃ£o em desenvolvimento',
      description: 'Aqui entraremos com o OAuth do Meta Ads para este cliente.',
    });
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
          <h2 className="text-xl font-semibold text-slate-900">Cliente nÃ£o encontrado</h2>
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
        <title>ConexÃ£o - {client.name} | DashFlow</title>
        <meta name="description" content="Gerencie conexÃµes e campanhas do cliente" />
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
                {client.company || 'Empresa nÃ£o informada'} {client.email ? `â€¢ ${client.email}` : ''}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Plug className="w-5 h-5 text-[#2563EB]" />
                <h2 className="text-lg font-semibold text-slate-900">ConexÃµes</h2>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between border border-slate-200 rounded-lg p-4">
                  <div>
                    <p className="font-medium text-slate-900">Google Ads</p>
                    <p className="text-sm text-slate-500">Conecte a conta do cliente</p>
                  </div>
                  <Button onClick={handleConnectGoogle} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                    Conectar
                  </Button>
                </div>
                <div className="flex items-center justify-between border border-slate-200 rounded-lg p-4">
                  <div>
                    <p className="font-medium text-slate-900">Meta Ads</p>
                    <p className="text-sm text-slate-500">Conecte a conta do cliente</p>
                  </div>
                  <Button onClick={handleConnectMeta} variant="outline">
                    Conectar
                  </Button>
                </div>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-[#2563EB]" />
                <h2 className="text-lg font-semibold text-slate-900">Campanhas</h2>
              </div>
              <div className="text-center py-10">
                <Link2Off className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <p className="text-slate-500">Nenhuma campanha conectada ainda.</p>
                <p className="text-sm text-slate-400 mt-1">Conecte uma integraÃ§Ã£o para ver as campanhas deste cliente.</p>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    </>
  );
};

export default ClientConnection;
