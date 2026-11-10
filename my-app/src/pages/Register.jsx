import AuthLayout from '@/components/AuthLayout';
import React, { useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const result = await register(name, email, password);
    if (result.success) {
      // ✅ Limpa os campos
      setName('');
      setEmail('');
      setPassword('');

      // ✅ Redireciona para o login
      navigate('/login');
    } else {
      setError(result.error);
    }
  };

  return (<><Helmet><title>Criar conta — DASH</title></Helmet><AuthLayout>
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-slate-100 mb-2">Crie sua conta</h2>
              <p className="text-slate-300">Preencha os dados abaixo para começar</p>
            </div>

            <div role="alert" className="text-red-300">{error}</div>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-slate-200">Nome completo</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    id="name" autoComplete="name"
                    type="text"
                    placeholder="Seu nome"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="pl-10 h-12 bg-background border-input text-slate-100 focus:border-[#2563EB]"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-200">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    id="email" autoComplete="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10 h-12 bg-background border-input text-slate-100 focus:border-[#2563EB]"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-200">Senha</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    id="password" autoComplete="new-password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 h-12 bg-background border-input text-slate-100 focus:border-[#2563EB]"
                    required
                  />
                </div>
              </div>

              <Button type="submit" className="w-full h-12 bg-[#2563EB] hover:bg-[#1E4FD1] text-white font-medium">
                Criar conta
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-slate-300">
                Já tem uma conta?{' '}
                <Link to="/login" className="text-blue-300 hover:text-blue-200 font-medium">
                  Faça login
                </Link>
              </p>
            </div>

  </AuthLayout></>);
};
export default Register;
