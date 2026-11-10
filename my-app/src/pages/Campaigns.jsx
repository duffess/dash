import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import Layout from '@/components/Layout';
import CampaignCard from '@/campaigns/CampaignCard';
import { Button } from '@/components/ui/button';
import { Plus, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

const Campaigns = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [error, setError] = useState('');
  const [clientsError, setClientsError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    api.get('/clients/').then(({ data }) => {
      if (active) { setClients(data); setClientsError(''); }
    }).catch(() => {
      if (active) setClientsError('Não foi possível carregar os clientes. Tente novamente.');
    });
    return () => { active = false; };
  }, [retry]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setCampaigns([]);
    api.get('/campaigns/', { params: selectedClient ? { client_id: selectedClient } : {} })
      .then(({ data }) => { if (active) setCampaigns(data); })
      .catch((err) => {
        if (active) setError(err.response?.data?.detail || 'Não foi possível carregar as campanhas.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selectedClient, retry]);

  const filteredCampaigns = campaigns.filter(campaign =>
    campaign.name.toLowerCase().includes(searchTerm.toLowerCase())
  );



  return (
    <>
      <Helmet>
        <title>Campanhas — DASH</title>
        <meta name="description" content="Consulte campanhas de Google Ads e Meta Ads" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-100">Campanhas</h1>
              <p className="text-slate-300 mt-1">Gerencie e monitore suas campanhas ativas</p>
            </div>
            <Button disabled title="Crie campanhas diretamente na plataforma de anúncios" className="bg-[#2563EB] hover:bg-[#1E4FD1]">
              <Plus className="w-5 h-5 mr-2" />
              Criação em breve
            </Button>
          </div>

          <div className="space-y-2">
            <label htmlFor="campaign-client" className="text-sm font-medium text-slate-200">Cliente</label>
            <select
              id="campaign-client"
              value={selectedClient}
              onChange={(event) => setSelectedClient(event.target.value)}
              className="w-full rounded-md border border-input bg-card px-3 py-2 text-slate-100"
            >
              <option value="">Todos os clientes</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
            <p className="text-sm text-slate-400">Métricas dos últimos 30 dias, conforme a última sincronização.</p>
          </div>

          {(error || clientsError) && (
            <div role="alert" className="rounded-lg border border-red-400/30 p-4 text-red-300">
              <p>{error || clientsError}</p>
              <Button variant="outline" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</Button>
            </div>
          )}
          {loading && <p role="status" className="text-slate-400">Carregando campanhas...</p>}

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <Input
              aria-label="Buscar campanhas" placeholder="Buscar campanhas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-card border-input focus:border-[#2563EB]"
            />
          </div>

          <div className="grid grid-cols-1 gap-6">
            {filteredCampaigns.map((campaign, index) => (
              <motion.div
                key={campaign.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <CampaignCard campaign={campaign} />
              </motion.div>
            ))}
          </div>

          {!loading && !error && filteredCampaigns.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-400">{searchTerm ? "Nenhuma campanha corresponde à busca." : "Nenhuma campanha sincronizada. Conecte e sincronize a conta na página do cliente."}</p>
            </div>
          )}
        </div>
      </Layout>
    </>
  );
};

export default Campaigns;
