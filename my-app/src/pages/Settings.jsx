import React, { useState } from 'react';
import { Helmet } from 'react-helmet';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
import { Link2, Save } from 'lucide-react';

const Settings = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [googleAdsConnected, setGoogleAdsConnected] = useState(false);

  const handleConnectGoogleAds = () => {
    toast({
      title: "🚧 Integração em desenvolvimento",
      description: "A conexão com Google Ads estará disponível em breve! Por enquanto, estamos usando dados de demonstração.",
    });
  };

  const handleSaveSettings = () => {
    toast({
      title: "Configurações salvas!",
      description: "Suas preferências foram atualizadas com sucesso.",
    });
  };

  return (
    <>
      <Helmet>
        <title>Configurações - DashFlow</title>
        <meta name="description" content="Configure sua conta e integrações" />
      </Helmet>
      <Layout>
        <div className="space-y-6 max-w-3xl">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Configurações</h1>
            <p className="text-slate-600 mt-1">Gerencie sua conta e integrações</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Informações da Conta</h2>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Nome</Label>
                  <Input id="name" defaultValue={user?.name} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" defaultValue={user?.email} className="mt-1" disabled />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-200 pt-6">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">Integrações</h2>
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center border border-slate-200">
                      <img alt="Google Ads logo" className="w-8 h-8" src="https://images.unsplash.com/photo-1678483789111-3a04c4628bd6" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">Google Ads</p>
                      <p className="text-sm text-slate-600">
                        {googleAdsConnected ? 'Conectado' : 'Não conectado'}
                      </p>
                    </div>
                  </div>
                  <Button 
                    onClick={handleConnectGoogleAds}
                    variant={googleAdsConnected ? "outline" : "default"}
                    className={!googleAdsConnected ? "bg-[#2563EB] hover:bg-[#1E4FD1]" : ""}
                  >
                    <Link2 className="w-4 h-4 mr-2" />
                    {googleAdsConnected ? 'Reconectar' : 'Conectar'}
                  </Button>
                </div>
              </div>
            </div>

            <div className="border-t border-slate-200 pt-6">
              <Button onClick={handleSaveSettings} className="bg-[#2563EB] hover:bg-[#1E4FD1]">
                <Save className="w-4 h-4 mr-2" />
                Salvar Alterações
              </Button>
            </div>
          </div>
        </div>
      </Layout>
    </>
  );
};

export default Settings;
