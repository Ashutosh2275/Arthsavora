import React, { useState, useEffect, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Landmark,
  Wallet,
  Target,
  LogOut,
  ShieldCheck,
  Trophy,
  FileText,
  Receipt,
  BookOpen,
  Upload,
  Tag,
  Menu,
  X,
  Repeat,
  TrendingUp,
  ShieldAlert,
  Bot,
  Bell,
  Users,
} from 'lucide-react';
import AIChatbot from '@/components/AIChatbot';
import useAuthStore from '@/store/useAuthStore';
import { useNotificationStore } from '@/store/useNotificationStore';
import { Toaster } from 'sonner';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { logout } = useAuthStore();
  const { unreadCount, fetchUnreadCount } = useNotificationStore();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    fetchUnreadCount();
  }, []);

  const navItems = [
    { name: 'Analytics', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { name: 'Accounts', path: '/accounts', icon: <Landmark size={18} /> },
    { name: 'Transactions', path: '/transactions', icon: <Receipt size={18} /> },
    { name: 'Ledger', path: '/ledger', icon: <BookOpen size={18} /> },
    { name: 'Import', path: '/import', icon: <Upload size={18} /> },
    { name: 'Receipts', path: '/documents', icon: <FileText size={18} /> },
    { name: 'Categories', path: '/categories', icon: <Tag size={18} /> },
    { name: 'Expenses', path: '/expenses', icon: <Wallet size={18} /> },
    { name: 'Budgets', path: '/budgets', icon: <Target size={18} /> },
    { name: 'Goals', path: '/goals', icon: <Trophy size={18} /> },
    { name: 'Recurring', path: '/recurring', icon: <Repeat size={18} /> },
    { name: 'Family', path: '/family', icon: <Users size={18} /> },
    { name: 'Forecast', path: '/forecast', icon: <TrendingUp size={18} /> },
    { name: 'Security & Risk', path: '/anomalies', icon: <ShieldAlert size={18} /> },
    { name: 'Alerts', path: '/notifications', icon: <Bell size={18} /> },
    { name: 'AI Assistant', path: '/assistant', icon: <Bot size={18} /> },
    { name: 'Reports', path: '/reports', icon: <FileText size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white flex flex-col">
      <Toaster position="top-right" theme="dark" richColors />

      {/* Top Header */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-slate-900/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <Link to="/dashboard" className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-lg">
              <ShieldCheck className="text-indigo-500" size={24} />
              <span className="text-lg font-black tracking-tight text-white uppercase">
                ARTHSAVORA
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
              {navItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    aria-current={isActive ? 'page' : undefined}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                      isActive
                        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    {item.icon}
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/notifications"
              aria-label="View notifications"
              className="relative p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white shadow-sm ring-2 ring-slate-900 animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Link>

            <button
              onClick={logout}
              aria-label="Sign out of Arthsavora"
              className="hidden sm:flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 transition-colors hover:bg-rose-500/10 hover:text-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
            >
              <LogOut size={16} />
              <span>Sign Out</span>
            </button>

            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
              className="md:hidden rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <nav
            className="md:hidden border-t border-slate-800 bg-slate-900/95 px-4 pt-3 pb-4 space-y-1"
            aria-label="Mobile Navigation"
          >
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
                  }`}
                >
                  {item.icon}
                  <span>{item.name}</span>
                </Link>
              );
            })}
            <div className="pt-2 border-t border-slate-800 mt-2">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  logout();
                }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut size={18} />
                <span>Sign Out</span>
              </button>
            </div>
          </nav>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        {children}
      </main>

      {/* Global AI Financial Assistant */}
      <AIChatbot />
    </div>
  );
}

export default AppLayout;
