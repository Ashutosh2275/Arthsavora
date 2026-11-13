import React, { type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Wallet,
  Target,
  LogOut,
  ShieldCheck,
  Trophy,
  FileText,
} from 'lucide-react';
import AIChatbot from '@/components/AIChatbot';
import useAuthStore from '@/store/useAuthStore';
import { Toaster } from 'sonner';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { logout } = useAuthStore();
  const location = useLocation();

  const navItems = [
    { name: 'Analytics', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { name: 'Expenses', path: '/expenses', icon: <Wallet size={18} /> },
    { name: 'Budget & AI', path: '/budget', icon: <Target size={18} /> },
    { name: 'Milestones', path: '/goals', icon: <Trophy size={18} /> },
    { name: 'Reports', path: '/reports', icon: <FileText size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white">
      <Toaster position="top-right" theme="dark" richColors />

      <header className="sticky top-0 z-50 border-b border-white/5 bg-slate-900/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <Link to="/dashboard" className="flex items-center gap-2">
              <ShieldCheck className="text-indigo-500" size={24} />
              <span className="text-lg font-black tracking-tight text-white uppercase">
                ARTHSAVORA
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                    }`}
                  >
                    {item.icon}
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 transition-all hover:bg-rose-500/10 hover:text-rose-400"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>

      {/* Global AI Financial Assistant */}
      <AIChatbot />
    </div>
  );
}

export default AppLayout;
