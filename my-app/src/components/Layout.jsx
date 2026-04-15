import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Users, Megaphone, FileText, Settings, LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Clientes', href: '/clients', icon: Users },
    { name: 'Campanhas', href: '/campaigns', icon: Megaphone },
    { name: 'Relatórios', href: '/reports', icon: FileText },
    { name: 'Configurações', href: '/settings', icon: Settings },
  ];

  const handleLogout = () => {
    logout();
    toast({
      title: "Logout realizado",
      description: "Até logo! 👋",
    });
    navigate('/login');
  };

  const activeItem = navigation.find(n => n.href === location.pathname) || { name: 'DashFlow' };

  return (
    <div className="min-h-screen bg-[#0B1326] text-slate-100 selection:bg-[#2563EB]/30">
      {/* Sidebar Desktop */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 bg-[#131B2E] lg:flex flex-col z-50">
        <div className="p-8">
          <Link to="/dashboard" className="flex items-center gap-2 group">
            <span className="text-2xl font-black text-white brand-logo tracking-[0.2em] group-hover:text-[#2563EB] transition-colors">DASH</span>
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1 mt-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link key={item.name} to={item.href} className="block group">
                <div className={`
                  flex items-center px-4 py-3 text-sm font-medium transition-all duration-200
                  ${isActive 
                    ? 'bg-[#2563EB] text-white' 
                    : 'text-slate-400 hover:bg-[#1E293B] hover:text-white'}
                `}>
                  <Icon className={`w-5 h-5 mr-3 transition-colors ${isActive ? 'text-white' : 'group-hover:text-[#2563EB]'}`} />
                  <span className={isActive ? 'font-bold' : ''}>{item.name.toUpperCase()}</span>
                  {isActive && <motion.div layoutId="activeNav" className="ml-auto"><ChevronRight className="w-4 h-4" /></motion.div>}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 mt-auto">
          <button 
            onClick={handleLogout}
            className="flex items-center w-full px-4 py-3 text-sm font-medium text-slate-400 hover:bg-[#1E293B] hover:text-white transition-all group"
          >
            <LogOut className="w-5 h-5 mr-3 group-hover:text-red-500 transition-colors" />
            <span>SAIR</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Header / Topbar */}
        <header className="sticky top-0 z-40 h-20 glass flex items-center justify-between px-8 border-none lg:px-12">
          <div className="flex items-center lg:hidden">
             <span className="text-xl font-black text-white brand-logo tracking-[0.15em]">DASH</span>
          </div>
          
          <div className="hidden lg:block">
            <h2 className="text-xs font-bold text-[#2563EB] tracking-[0.3em] uppercase mb-1">Navigation / {activeItem.name}</h2>
            <h1 className="text-2xl font-black text-white tracking-tight leading-none uppercase">{activeItem.name}</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col items-end mr-2">
              <span className="text-sm font-bold text-white uppercase tracking-wider">{user?.name || 'User'}</span>
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.1em]">Account Active</span>
            </div>
            <div className="w-10 h-10 grad-dash flex items-center justify-center text-white font-bold text-lg select-none">
              {user?.name?.[0] || 'U'}
            </div>
            <button 
              className="lg:hidden p-2 text-white"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-8 lg:p-12 max-w-[1600px] w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] lg:hidden"
            />
            <motion.div 
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-72 bg-[#131B2E] z-[70] lg:hidden flex flex-col p-8"
            >
              <div className="flex justify-between items-center mb-12">
                <span className="text-2xl font-black text-white brand-logo">DASH</span>
                <button onClick={() => setMobileMenuOpen(false)}>
                  <X className="w-6 h-6 text-white" />
                </button>
              </div>

              <div className="space-y-4">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link key={item.name} to={item.href} onClick={() => setMobileMenuOpen(false)}>
                      <div className="flex items-center p-4 text-white font-bold tracking-wider hover:bg-[#2563EB] transition-colors">
                        <Icon className="w-5 h-5 mr-4" />
                        {item.name.toUpperCase()}
                      </div>
                    </Link>
                  );
                })}
              </div>

              <button 
                onClick={handleLogout}
                className="mt-auto flex items-center p-4 text-slate-400 font-bold tracking-wider"
              >
                <LogOut className="w-5 h-5 mr-4" />
                SAIR
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Layout;
