import React, { useState } from 'react';
import { Download, Share2, PlusSquare, Monitor, CheckCircle2, X } from 'lucide-react';
import { usePwaStore } from '@/pwa/usePwaStore';
import { Button } from '@/components/ui/button';

interface InstallPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InstallPromptModal: React.FC<InstallPromptModalProps> = ({ isOpen, onClose }) => {
  const { isInstallable, isInstalled, promptInstall } = usePwaStore();
  const [installStatus, setInstallStatus] = useState<string | null>(null);

  if (!isOpen) return null;

  // Determine if iOS Safari
  const isIos =
    typeof navigator !== 'undefined' &&
    /iPad|iPhone|iPod/.test(navigator.userAgent) &&
    !(window as any).MSStream;

  const handleInstallClick = async () => {
    const outcome = await promptInstall();
    if (outcome === 'accepted') {
      setInstallStatus('installed');
      setTimeout(() => onClose(), 1500);
    } else if (outcome === 'dismissed') {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="install-modal-title"
        className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-5 animate-in zoom-in-95"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Download size={20} />
            </div>
            <div>
              <h3 id="install-modal-title" className="text-base font-bold text-white">
                Install ARTHSAVORA App
              </h3>
              <p className="text-xs text-slate-400">Progressive Web Application</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            aria-label="Close install dialog"
          >
            <X size={18} />
          </button>
        </div>

        {isInstalled || installStatus === 'installed' ? (
          <div className="py-6 text-center space-y-2">
            <CheckCircle2 size={40} className="text-emerald-400 mx-auto" />
            <h4 className="text-sm font-semibold text-white">App Installed Successfully!</h4>
            <p className="text-xs text-slate-400">
              You can now launch ARTHSAVORA directly from your home screen or application launcher.
            </p>
          </div>
        ) : (
          <div className="space-y-4 text-xs text-slate-300">
            <p className="leading-relaxed">
              Experience fast financial management, offline application shell caching, full-screen viewports, and instant notifications.
            </p>

            {isIos ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-3">
                <span className="font-semibold text-white block">iOS Installation Instructions:</span>
                <ol className="space-y-2 text-slate-300 list-decimal list-inside">
                  <li className="flex items-center gap-2">
                    <Share2 size={14} className="text-indigo-400 shrink-0" />
                    <span>Tap the <strong>Share</strong> button in Safari's toolbar</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <PlusSquare size={14} className="text-indigo-400 shrink-0" />
                    <span>Scroll down and select <strong>Add to Home Screen</strong></span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    <span>Tap <strong>Add</strong> in the top-right corner</span>
                  </li>
                </ol>
              </div>
            ) : isInstallable ? (
              <div className="space-y-3">
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 flex items-center gap-3">
                  <Monitor size={18} className="text-indigo-400 shrink-0" />
                  <div>
                    <span className="font-semibold text-white block">Standalone Window Experience</span>
                    <span className="text-slate-400 text-[11px]">
                      Runs outside of browser tabs with native window controls and launch shortcuts.
                    </span>
                  </div>
                </div>

                <Button
                  variant="primary"
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500"
                  onClick={handleInstallClick}
                >
                  <Download size={15} />
                  Install Now
                </Button>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
                <span className="font-semibold text-white block">Browser Installation:</span>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Use your browser menu (e.g. Chrome/Edge) and select <strong>Install ARTHSAVORA</strong> or look for the install icon in your address bar.
                </p>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end pt-2">
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
