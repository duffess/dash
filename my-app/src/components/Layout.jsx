import React, { useEffect } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Megaphone, FileText, Settings, LogOut, ChevronRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
const navigation = [
  { name: 'Visão geral', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Clientes', href: '/clients', icon: Users },
  { name: 'Campanhas', href: '/campaigns', icon: Megaphone },
  { name: 'Relatórios', href: '/reports', icon: FileText },
  { name: 'Configurações', mobileName: 'Ajustes', href: '/settings', icon: Settings },
];
export default function Layout({ children }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const active = navigation.find(item => pathname.startsWith(item.href));
  const handleLogout = () => {
    logout();
    toast({ title: 'Você saiu da conta', description: 'Até a próxima.' });
    navigate('/login');
  };
  return <div className="dash-app">
    <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
    <aside className="dash-sidebar dash-panel">
      <Link className="dash-brand" to="/dashboard" aria-label="DASH — início"><span className="brand-logo">DASH</span><span>Data. Performance. Clarity.</span></Link>
      <div className="nav-caption">ESPAÇO DE TRABALHO</div>
      <nav aria-label="Navegação principal" className="dash-navigation">
        {navigation.map(({ name, mobileName, href, icon: Icon }) => <NavLink key={href} to={href} className={({ isActive }) => `dash-nav-link ${isActive ? 'is-active' : ''}`}>
          <Icon size={20} aria-hidden="true" /><span className={mobileName ? "nav-label-desktop" : ""}>{name}</span>{mobileName && <span className="nav-label-mobile">{mobileName}</span>}<ChevronRight size={14} className="nav-arrow" aria-hidden="true" />
        </NavLink>)}
      </nav>
      <div className="sidebar-bottom"><span className="sidebar-signature">Menos ruído.<br /><strong>Mais clareza.</strong></span><button onClick={handleLogout} className="dash-nav-link"><LogOut size={19} aria-hidden="true" /><span>Sair da conta</span></button></div>
    </aside>
    <div className="dash-workspace">
      <header className="dash-topbar">
        <div><Link to="/dashboard" className="brand-logo mobile-brand">DASH</Link><span className="desktop-breadcrumb">Seu workspace <ChevronRight size={14} aria-hidden="true" /> <strong>{active?.name || 'Cliente'}</strong></span></div>
        <div className="account-area"><div className="account-name"><strong>{user?.name || 'Minha conta'}</strong><span>Conta da agência</span></div><Link to="/settings" className="account-avatar" aria-label="Abrir configurações da conta">{user?.name?.[0]?.toUpperCase() || 'D'}</Link><button className="mobile-logout" onClick={handleLogout} aria-label="Sair da conta"><LogOut size={20} /></button></div>
      </header>
      <main id="main-content" tabIndex={-1} className="dash-main">{children}</main>
      <footer className="dash-footer"><span>DASH / Data. Performance. Clarity.</span><span>Seu espaço de resultados</span></footer>
    </div>
  </div>;
}
