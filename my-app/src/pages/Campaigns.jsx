import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import Layout from '@/components/Layout';
import CampaignCard from '@/campaigns/CampaignCard';
import { Button } from '@/components/ui/button';
import { Plus, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

const Campaigns = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const { data } = await api.get('/campaigns/');
      setCampaigns(data);
    } catch (error) {
      // Se não tiver endpoint ainda, usa mock
      const mockCampaigns = [
        {
          id: '1',
          name: 'Campanha Black Friday 2024',
          status: 'active',
          budget: 5000,
          spent: 3245.80,
          impressions: 52340,
          clicks: 1876,
          conversions: 143,
          ctr: 3.58,
          cpc: 1.73,
        },
        {
          id: '2',
          name: 'Remarketing - Carrinho Abandonado',
          status: 'active',
          budget: 2000,
          spent: 1567.30,
          impressions: 28450,
          clicks: 892,
          conversions: 67,
          ctr: 3.14,
          cpc: 1.76,
        },
      ];
      setCampaigns(mockCampaigns);
      
      toast({
        title: "Modo demonstração",
        description: "Exibindo campanhas de exemplo. Conecte sua conta Google Ads para ver dados reais.",
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredCampaigns = campaigns.filter(campaign =>
    campaign.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleNewCampaign = () => {
    toast({
      title: "🚧 Funcionalidade em desenvolvimento",
      description: "A criação de campanhas estará disponível em breve!",
    });
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-600">Carregando campanhas...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <>
      <Helmet>
        <title>Campanhas - DashFlow</title>
        <meta name="description" content="Gerencie suas campanhas de Google Ads" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Campanhas</h1>
              <p className="text-slate-600 mt-1">Gerencie e monitore suas campanhas ativas</p>
            </div>
            <Button onClick={handleNewCampaign} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
              <Plus className="w-5 h-5 mr-2" />
              Nova Campanha
            </Button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <Input
              placeholder="Buscar campanhas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-white border-slate-300 focus:border-[#2563EB]"
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

          {filteredCampaigns.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-500">Nenhuma campanha encontrada</p>
            </div>
          )}
        </div>
      </Layout>
    </>
  );
};

export default Campaigns;
