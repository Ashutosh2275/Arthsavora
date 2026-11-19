import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Menu,
  Bell,
  Sparkles,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Download,
  Wifi,
  WifiOff,
} from 'lucide-react';
import useAuthStore from '@/store/useAuthStore';
import { useNotificationStore } from '@/store/useNotificationStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';
import { usePwaStore } from '@/pwa/usePwaStore';
import WorkspaceSwitcher from './WorkspaceSwitcher';
import GlobalSearch from './GlobalSearch';
import ThemeToggle from '../ui/ThemeToggle';
import { InstallPromptModal } from '../pwa/InstallPromptModal';

interface TopBarProps {
  onMobileMenuToggle: () => void;
  onAssistantToggle?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onMobileMenuToggle, onAssistantToggle }) => {
  const { user, logout } = useAuthStore();
  const { unreadCount, fetchUnreadCount } = useNotificationStore();
  const { activeWorkspace } = useWorkspaceStore();
  const { isInstallable, isOffline } = usePwaStore();
  const location = useLocation();

  const [profileOpen, setProfileOpen] = useState(false);
  const [installModalOpen, setInstallModalOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchUnreadCount();
  }, []);

  // Close profile dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Format current page breadcrumb
  const getBreadcrumbTitle = () => {
    const path = location.pathname.replace('/', '');
    if (!path || path === 'dashboard') return 'Financial Analytics';
    return path
      .split('-')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const userInitials = (user?.full_name || user?.email || 'U')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  return (
    <>
      <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left: Mobile Menu & Breadcrumbs */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMobileMenuToggle}
            aria-label="Open mobile navigation menu"
            className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Menu size={20} />
          </button>

          <div className="hidden sm:flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Arthsavora</span>
            <span className="text-slate-600">/</span>
            <span className="text-white font-semibold">{getBreadcrumbTitle()}</span>
          </div>

          {/* Network Status Dot */}
          <div
            title={isOffline ? 'Offline Mode (Read-Only)' : 'Online & Synchronized'}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono border border-slate-800 bg-slate-950/60"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOffline ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'
              }`}
            />
            <span className="hidden md:inline text-slate-400">
              {isOffline ? 'Offline' : 'Live'}
            </span>
          </div>
        </div>

        {/* Center: Global Search Bar */}
        <div className="flex-1 max-w-md mx-2">
          <GlobalSearch />
        </div>

        {/* Right: Actions, Switcher, Theme, Profile */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* PWA Install Button (Promptable or on-demand) */}
          <button
            type="button"
            onClick={() => setInstallModalOpen(true)}
            aria-label="Install ARTHSAVORA App"
            title="Install ARTHSAVORA App"
            className={`p-2 rounded-xl border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 flex items-center gap-1.5 text-xs font-medium ${
              isInstallable
                ? 'bg-indigo-600/10 text-indigo-400 border-indigo-500/30 hover:bg-indigo-600/20'
                : 'text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Download size={15} />
            <span className="hidden xl:inline">Install App</span>
          </button>

          {/* Workspace Switcher */}
          <div className="hidden md:block">
            <WorkspaceSwitcher />
          </div>

          {/* Quick AI Assistant Trigger */}
          <Link
            to="/assistant"
            aria-label="Open AI Financial Assistant"
            className="p-2 rounded-xl text-indigo-400 hover:text-indigo-300 hover:bg-indigo-600/10 transition-colors border border-indigo-500/20 hidden sm:flex items-center gap-1.5 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Sparkles size={15} />
            <span className="hidden xl:inline">AI Co-pilot</span>
          </Link>

          {/* Notifications Bell */}
          <Link
            to="/notifications"
            aria-label="View notifications"
            className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white shadow-sm ring-2 ring-slate-900 animate-pulse">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </Link>

          {/* Theme Toggle */}
          <div className="hidden sm:block">
            <ThemeToggle />
          </div>

          {/* Profile Menu Dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              onClick={() => setProfileOpen((prev) => !prev)}
              aria-expanded={profileOpen}
              aria-label="User profile menu"
              className="flex items-center gap-2 p-1 pl-1.5 pr-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white font-bold text-xs flex items-center justify-center shadow-inner">
                {userInitials}
              </div>
              <ChevronDown
                size={12}
                className={`text-slate-400 transition-transform ${profileOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {profileOpen && (
              <div
                role="menu"
                aria-label="Profile Menu"
                className="absolute right-0 mt-2 w-56 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-2 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 space-y-1 text-xs"
              >
                <div className="px-3 py-2 border-b border-slate-800 mb-1">
                  <p className="font-semibold text-white truncate">{user?.full_name || 'Financial Member'}</p>
                  <p className="text-[11px] text-slate-400 truncate">{user?.email || 'user@arthsavora.internal'}</p>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                      {activeWorkspace?.type || 'Personal'} Workspace
                    </span>
                  </div>
                </div>

                <div className="md:hidden px-2 py-1.5 border-b border-slate-800">
                  <p className="text-[10px] text-slate-500 uppercase font-mono mb-1">Theme</p>
                  <ThemeToggle />
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false);
                    setInstallModalOpen(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <Download size={14} className="text-slate-400" />
                  <span>Install Web App</span>
                </button>

                <Link
                  to="/settings"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <Settings size={14} className="text-slate-400" />
                  <span>Account &amp; Settings</span>
                </Link>

                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false);
                    logout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <LogOut size={14} />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Install PWA Modal */}
      <InstallPromptModal isOpen={installModalOpen} onClose={() => setInstallModalOpen(false)} />
    </>
  );
};

export default TopBar;
