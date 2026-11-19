import React, { useState, useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { Toaster } from 'sonner';
import AIChatbot from '@/components/AIChatbot';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MobileTabBar from './MobileTabBar';
import OnboardingModal from './OnboardingModal';
import { OfflineBanner } from '../pwa/OfflineBanner';
import { UpdatePrompt } from '../pwa/UpdatePrompt';
import { initServiceWorker } from '@/pwa/registerServiceWorker';
import { useThemeStore } from '@/store/useThemeStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { initTheme } = useThemeStore();
  const { fetchWorkspaces } = useWorkspaceStore();

  useEffect(() => {
    initTheme();
    fetchWorkspaces();
    const cleanupSw = initServiceWorker();
    return () => {
      cleanupSw();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white flex flex-col lg:flex-row">
      <Toaster position="top-right" theme="dark" richColors />

      {/* Skip to Main Content Link (Accessibility WCAG 2.2 AA) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded-lg focus:shadow-lg focus:outline-none"
      >
        Skip to main content
      </a>

      {/* Desktop Sidebar (lg and above) */}
      <div className="hidden lg:flex">
        <Sidebar className="sticky top-0 h-screen" />
      </div>

      {/* Mobile Drawer (Overlay when open) */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Mobile Navigation Menu"
            className="relative flex-1 flex flex-col max-w-xs w-full bg-slate-900 border-r border-slate-800 shadow-2xl z-50 animate-in slide-in-from-left duration-200"
          >
            <div className="absolute top-3 right-3 z-50">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close navigation menu"
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                <X size={20} />
              </button>
            </div>
            <Sidebar onItemClick={() => setMobileMenuOpen(false)} className="w-full h-full border-r-0" />
          </div>
        </div>
      )}

      {/* Main App Content Layout */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Offline Notification Banner */}
        <OfflineBanner />

        {/* Top Header Command Center */}
        <TopBar onMobileMenuToggle={() => setMobileMenuOpen((prev) => !prev)} />

        {/* Main Content Area */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 pb-24 md:pb-8 focus:outline-none"
        >
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar */}
      <MobileTabBar />

      {/* PWA Update Notice */}
      <UpdatePrompt />

      {/* Global AI Assistant Floating Co-Pilot */}
      <AIChatbot />

      {/* First-Time User Onboarding Modal */}
      <OnboardingModal />
    </div>
  );
}

export default AppLayout;
