import React, { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Search, Link2, Trash2, Users } from 'lucide-react';
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
  const [loadError, setLoadError] = useState('');
  const [overview, setOverview] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState(null);
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
    setLoading(true); setLoadError('');
    try {
      const { data } = await api.get('/clients/');
      setClients(data);
      try { const summary = await api.get('/clients/overview'); setOverview(Object.fromEntries(summary.data.map(row => [row.client_id, row]))); } catch { setOverview(null); }
    } catch (error) {
      setLoadError('Não foi possível carregar os clientes.');
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
        title: 'Nome obrigatório',
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
      const { data } = editingId ? await api.put(`/clients/${editingId}`, payload) : await api.post('/clients/', payload);
      setClients((prev) => editingId ? prev.map(client => client.id === editingId ? data : client) : [data, ...prev]);
      if (!editingId) setOverview(prev => prev ? {...prev, [data.id]: {client_id: data.id, campaign_count: 0, last_report_at: null}} : null);
      setEditingId(null);
      setForm({ name: '', email: '', phone: '', company: '' });
      toast({ title: editingId ? 'Cliente atualizado' : 'Cliente criado', description: 'Dados salvos com sucesso.' });
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
    const client = clients.find(item => item.id === clientId);
    const confirmed = window.confirm(`Excluir ${client?.name || 'este cliente'}? As campanhas, conexões e relatórios associados também serão excluídos. Esta ação não pode ser desfeita.`);
    if (!confirmed) return;

    try {
      await api.delete(`/clients/${clientId}`);
      setClients((prev) => prev.filter((client) => client.id !== clientId));
      if (editingId === clientId) { setEditingId(null); setForm({name: '', email: '', phone: '', company: ''}); }
      toast({ title: 'Cliente removido', description: 'Cliente excluído com sucesso.' });
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
        <title>Clientes — DASH</title>
        <meta name="description" content="Gerencie seus clientes e conexões" />
      </Helmet>
      <Layout>
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-100">Clientes</h1>
              <p className="text-slate-300 mt-1">Cadastre clientes e acesse a página de conexão</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_2fr] gap-6">
            <div className="dash-panel p-6 space-y-4" id="client-form">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-300" />
                <h2 className="text-lg font-semibold text-slate-100">{editingId ? 'Editar cliente' : 'Adicionar cliente'}</h2>
              </div>
              <p className="text-sm text-slate-300">Os dados de contato são opcionais e podem ser alterados depois.</p><form className="space-y-4 client-form" onSubmit={handleCreateClient}>
                <div className="space-y-2">
                  <Label htmlFor="name">Nome do cliente *</Label>
                  <Input id="name" name="name" required value={form.name} onChange={handleChange} placeholder="Ex.: Café Horizonte" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">Empresa ou marca <span className="text-slate-400">(opcional)</span></Label>
                  <Input id="company" name="company" value={form.company} onChange={handleChange} placeholder="Ex.: Café Horizonte" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">E-mail <span className="text-slate-400">(opcional)</span></Label>
                  <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} placeholder="contato@exemplo.com.br" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Telefone <span className="text-slate-400">(opcional)</span></Label>
                  <Input id="phone" name="phone" type="tel" autoComplete="tel" value={form.phone} onChange={handleChange} placeholder="(21) 99999-9999" />
                </div>
                <Button type="submit" className="w-full bg-[#2563EB] hover:bg-[#1E4FD1]" disabled={saving}>
                  {saving ? 'Salvando...' : editingId ? 'Salvar alterações' : 'Adicionar cliente'}
                </Button>
                {editingId && <Button type="button" variant="outline" className="w-full" onClick={() => {setEditingId(null); setForm({name: '', email: '', phone: '', company: ''});}}>Cancelar edição</Button>}
              </form>
            </div>

            <div className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  aria-label="Buscar clientes" placeholder="Buscar clientes..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="pl-10 bg-card border-input"
                />
              </div>

              {loading ? (
                <div className="flex items-center justify-center h-48 dash-panel">
                  <div className="text-center">
                    <div className="w-10 h-10 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                    <p className="text-slate-300">Carregando clientes...</p>
                  </div>
                </div>
              ) : loadError ? <div role="alert" className="dash-panel p-5"><p>{loadError}</p><Button variant="outline" onClick={fetchClients}>Tentar novamente</Button></div> : (
                <div className="space-y-4">
                  {filteredClients.map((client, index) => (
                    <motion.div
                      key={client.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="dash-panel p-5"
                    >
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                          <h3 className="text-lg font-semibold text-slate-100">{client.name}</h3>
                          <p className="text-slate-400 text-sm">{client.company || 'Empresa não informada'}</p>
                          <div className="text-sm text-slate-400 mt-2 space-y-1">
                            <p>{overview?.[client.id] ? `${overview[client.id].campaign_count} campanha(s) · ${overview[client.id].last_report_at ? 'Último relatório: ' + new Date(/Z$|[+-]\d\d:\d\d$/.test(overview[client.id].last_report_at) ? overview[client.id].last_report_at : overview[client.id].last_report_at + 'Z').toLocaleDateString('pt-BR') : 'Nenhum relatório salvo'}` : 'Resumo indisponível; abra o cliente para consultar.'}</p>
                            {client.email && <p>{client.email}</p>}
                            {client.phone && <p>{client.phone}</p>}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button variant="outline" onClick={() => handleOpenConnection(client.id)}>
                            <Link2 className="w-4 h-4 mr-2" />
                            Conexão
                          </Button>
                          <Button variant="outline" onClick={() => navigate(`/campaigns?client_id=${encodeURIComponent(client.id)}`)}>Campanhas</Button>
                          <Button variant="outline" onClick={() => navigate(`/reports?client_id=${encodeURIComponent(client.id)}`)}>Relatórios</Button>
                          <Button variant="outline" onClick={() => {setEditingId(null); setForm({name: `${client.name} (cópia)`, company: client.company || '', email: client.email || '', phone: client.phone || ''}); document.getElementById('client-form')?.scrollIntoView({behavior: 'smooth'});}}>Duplicar dados</Button>
                          <Button variant="outline" onClick={() => {setEditingId(client.id); setForm({name: client.name || '', company: client.company || '', email: client.email || '', phone: client.phone || ''}); document.getElementById('client-form')?.scrollIntoView({behavior: 'smooth'});}}>Editar</Button>
                          <Button variant="ghost" onClick={() => handleDeleteClient(client.id)}>
                            <Trash2 className="w-4 h-4 mr-2 text-red-500" />
                            Excluir
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  {filteredClients.length === 0 && (
                    <div className="text-center py-12 dash-panel">
                      <p className="text-slate-400">{searchTerm ? 'Nenhum cliente corresponde à busca.' : 'Nenhum cliente cadastrado. Use o formulário para adicionar o primeiro.'}</p>
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
