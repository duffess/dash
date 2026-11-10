import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { ArrowRight, Link2, User } from 'lucide-react';
import Layout from '@/components/Layout';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';
export default function Settings() {
  const { user } = useAuth();
  return <><Helmet><title>Configurações — DASH</title></Helmet><Layout><div className="space-y-6 max-w-3xl">
    <div><h1 className="text-3xl text-white">Configurações</h1><p className="text-slate-300 mt-2">Sua conta e as conexões dos seus clientes.</p></div>
    <section className="dash-panel p-6 space-y-6"><div className="flex items-center gap-3"><User size={21} className="text-blue-300" aria-hidden="true" /><h2 className="text-lg font-semibold">Informações da conta</h2><span className="dash-chip ml-auto">Somente leitura</span></div><div className="space-y-4"><div><Label htmlFor="name">Nome</Label><Input id="name" value={user?.name || ''} readOnly className="mt-2" /></div><div><Label htmlFor="email">Email</Label><Input id="email" type="email" value={user?.email || ''} readOnly className="mt-2" /></div></div><p className="text-sm text-slate-300">A edição dos dados da conta ainda não está disponível.</p></section>
    <section className="dash-panel p-6"><div className="flex items-center gap-3 mb-4"><Link2 size={21} className="text-blue-300" aria-hidden="true" /><h2 className="text-lg font-semibold">Conexões de anúncios</h2></div><p className="text-slate-300">As contas do Google Ads e Meta Ads são conectadas por cliente. Acesse o cliente para consultar o status, selecionar a conta e sincronizar os dados.</p><Link to="/clients" className="dash-link mt-4">Gerenciar conexões nos clientes<ArrowRight size={16} aria-hidden="true" /></Link></section>
  </div></Layout></>;
}
