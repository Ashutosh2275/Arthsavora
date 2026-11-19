import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Landmark,
  Receipt,
  BookOpen,
  Upload,
  Tag,
  Target,
  Trophy,
  Repeat,
  TrendingUp,
  ShieldAlert,
  FileText,
  Users,
  Briefcase,
  Link2,
  Settings,
  LogOut,
  ChevronRight,
  ShieldCheck,
  Bot,
  Bell,
} from 'lucide-react';
import useAuthStore from '@/store/useAuthStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';

interface NavGroup {
  label: string;
  items: {
    name: string;
    path: string;
    icon: React.ReactNode;
    badge?: string;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Core Ledger & Accounts',
    items: [
      { name: 'Analytics Overview', path: '/dashboard', icon: <LayoutDashboard size={16} /> },
      { name: 'Accounts & Balances', path: '/accounts', icon: <Landmark size={16} /> },
      { name: 'Transactions', path: '/transactions', icon: <Receipt size={16} /> },
      { name: 'General Ledger', path: '/ledger', icon: <BookOpen size={16} /> },
      { name: 'Categories & Rules', path: '/categories', icon: <Tag size={16} /> },
      { name: 'Statement Import', path: '/import', icon: <Upload size={16} /> },
    ],
  },
  {
    label: 'Planning & Budgets',
    items: [
      { name: 'Spending Budgets', path: '/budgets', icon: <Target size={16} /> },
      { name: 'Financial Goals', path: '/goals', icon: <Trophy size={16} /> },
      { name: 'Recurring Finance', path: '/recurring', icon: <Repeat size={16} /> },
      { name: 'Cash Flow Forecast', path: '/forecast', icon: <TrendingUp size={16} /> },
    ],
  },
  {
    label: 'Intelligence & Compliance',
    items: [
      { name: 'Security & Risk', path: '/anomalies', icon: <ShieldAlert size={16} /> },
      { name: 'Receipts & OCR', path: '/documents', icon: <FileText size={16} /> },
      { name: 'Reports & Tax', path: '/reports', icon: <FileText size={16} /> },
      { name: 'Bank Connections', path: '/connections', icon: <Link2 size={16} /> },
      { name: 'AI Assistant', path: '/assistant', icon: <Bot size={16} /> },
      { name: 'Notification Center', path: '/notifications', icon: <Bell size={16} /> },
    ],
  },
  {
    label: 'Entity Workspaces',
    items: [
      { name: 'Family Household', path: '/family', icon: <Users size={16} /> },
      { name: 'Business Hub', path: '/business', icon: <Briefcase size={16} /> },
    ],
  },
];

interface SidebarProps {
  className?: string;
  onItemClick?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ className = '', onItemClick }) => {
  const location = useLocation();
  const { logout, user } = useAuthStore();
  const { activeWorkspace } = useWorkspaceStore();

  return (
    <aside
      className={`w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none ${className}`}
      aria-label="Application Sidebar Navigation"
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-slate-800/80 gap-3">
        <div className="rounded-xl bg-indigo-600 p-2 text-white shadow-lg shadow-indigo-600/30">
          <ShieldCheck size={20} />
        </div>
        <div>
          <span className="text-sm font-black tracking-tight text-white uppercase block leading-tight">
            ARTHSAVORA
          </span>
          <span className="text-[10px] text-indigo-400 font-mono tracking-wider">
            FINANCIAL OS
          </span>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6" aria-label="Main Navigation">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="space-y-1">
            <h4 className="px-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 font-mono">
              {group.label}
            </h4>
            {group.items.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onItemClick}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all group ${
                    isActive
                      ? 'bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <span className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'}>
                      {item.icon}
                    </span>
                    <span className="truncate">{item.name}</span>
                  </div>
                  {isActive && <ChevronRight size={12} className="text-indigo-200 shrink-0" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40 space-y-2">
        {/* Workspace Indicator */}
        <div className="px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/60 flex items-center justify-between text-[11px]">
          <span className="text-slate-400 truncate max-w-[120px] font-medium">
            {activeWorkspace?.name || 'Personal'}
          </span>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 uppercase">
            {activeWorkspace?.type || 'personal'}
          </span>
        </div>

        {/* User & Settings Quick Links */}
        <div className="flex items-center justify-between px-1">
          <Link
            to="/settings"
            onClick={onItemClick}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <Settings size={14} />
            <span>Settings</span>
          </Link>
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300 transition-colors"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
