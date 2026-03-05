import React, { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Link2, Trash2, Users } from 'lucide-react';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import api from '@/lib/api';

const Clients = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
  });

  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const { data } = await api.get('/clients/');
      setClients(data);
    } catch (error) {
      toast({
        title: 'Erro ao carregar clientes',
        description: error.response?.data?.detail || 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredClients = useMemo(() => {
    const term = searchTerm.toLowerCase();
    return clients.filter((client) =>
      client.name.toLowerCase().includes(term) ||
      (client.company || '').toLowerCase().includes(term) ||
      (client.email || '').toLowerCase().includes(term)
    );
  }, [clients, searchTerm]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateClient = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      toast({
        title: 'Nome obrigatÃ³rio',
        description: 'Informe o nome do cliente para continuar.',
        variant: 'destructive',
      });
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        company: form.company.trim() || null,
      };
      const { data } = await api.post('/clients/', payload);
      setClients((prev) => [data, ...prev]);
      setForm({ name: '', email: '', phone: '', company: '' });
      toast({ title: 'Cliente criado', description: 'Cliente adicionado com sucesso.' });
    } catch (error) {
      toast({
        title: 'Erro ao criar cliente',
        description: error.response?.data?.detail || 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClient = async (clientId) => {
    const confirmed = window.confirm('Deseja remover este cliente?');
    if (!confirmed) return;

    try {
      await api.delete(`/clients/${clientId}`);
      setClients((prev) => prev.filter((client) => client.id !== clientId));
      toast({ title: 'Cliente removido', description: 'Cliente excluÃ­do com sucesso.' });
    } catch (error) {
      toast({
        title: 'Erro ao excluir cliente',
        description: error.response?.data?.detail || 'Tente novamente em instantes.',
        variant: 'destructive',
      });
    }
  };

  const handleOpenConnection = (clientId) => {
    navigate(`/clients/${clientId}`);
  };

  return (
    <>
      <Helmet>
        <title>Clientes - DashFlow</title>
        <meta name="description" content="Gerencie seus clientes e conexÃµes" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Clientes</h1>
              <p className="text-slate-600 mt-1">Cadastre clientes e acesse a pÃ¡gina de conexÃ£o</p>
            </div>
            <Button className="bg-[#2563EB] hover:bg-[#1E4FD1]" onClick={() => document.getElementById('client-form')?.scrollIntoView({ behavior: 'smooth' })}>
              <Plus className="w-5 h-5 mr-2" />
              Novo Cliente
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_2fr] gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4" id="client-form">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-[#2563EB]" />
                <h2 className="text-lg font-semibold text-slate-900">Adicionar cliente</h2>
              </div>
              <form className="space-y-4" onSubmit={handleCreateClient}>
                <div className="space-y-2">
                  <Label htmlFor="name">Nome *</Label>
                  <Input id="name" name="name" value={form.name} onChange={handleChange} placeholder="Ex: AgÃªncia XYZ" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">Empresa</Label>
                  <Input id="company" name="company" value={form.company} onChange={handleChange} placeholder="XYZ Marketing Ltda" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} placeholder="contato@empresa.com" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Telefone</Label>
                  <Input id="phone" name="phone" value={form.phone} onChange={handleChange} placeholder="(21) 99999-9999" />
                </div>
                <Button type="submit" className="w-full bg-[#2563EB] hover:bg-[#1E4FD1]" disabled={saving}>
                  {saving ? 'Salvando...' : 'Adicionar cliente'}
                </Button>
              </form>
            </div>

            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  placeholder="Buscar clientes..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="pl-10 bg-white border-slate-300"
                />
              </div>

              {loading ? (
                <div className="flex items-center justify-center h-48 bg-white border border-slate-200 rounded-xl">
                  <div className="text-center">
                    <div className="w-10 h-10 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <p className="text-slate-600">Carregando clientes...</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredClients.map((client, index) => (
                    <motion.div
                      key={client.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="bg-white border border-slate-200 rounded-xl p-5"
                    >
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                          <h3 className="text-lg font-semibold text-slate-900">{client.name}</h3>
                          <p className="text-slate-500 text-sm">{client.company || 'Empresa nÃ£o informada'}</p>
                          <div className="text-sm text-slate-500 mt-2 space-y-1">
                            {client.email && <p>{client.email}</p>}
                            {client.phone && <p>{client.phone}</p>}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button variant="outline" onClick={() => handleOpenConnection(client.id)}>
                            <Link2 className="w-4 h-4 mr-2" />
                            ConexÃ£o
                          </Button>
                          <Button variant="ghost" onClick={() => handleDeleteClient(client.id)}>
                            <Trash2 className="w-4 h-4 mr-2 text-red-500" />
                            Excluir
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  {filteredClients.length === 0 && (
                    <div className="text-center py-12 bg-white border border-slate-200 rounded-xl">
                      <p className="text-slate-500">Nenhum cliente encontrado</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </Layout>
    </>
  );
};

export default Clients;
