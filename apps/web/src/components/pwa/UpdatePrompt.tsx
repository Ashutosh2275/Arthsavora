import React from 'react';
import { RefreshCw, X, Sparkles } from 'lucide-react';
import { usePwaStore } from '@/pwa/usePwaStore';
import { Button } from '@/components/ui/button';

export const UpdatePrompt: React.FC = () => {
  const hasUpdate = usePwaStore((state) => state.hasUpdate);
  const applyUpdate = usePwaStore((state) => state.applyUpdate);
  const dismissUpdate = usePwaStore((state) => state.dismissUpdate);

  if (!hasUpdate) {
    return null;
  }

  return (
    <aside
      role="region"
      aria-label="Application Update Notice"
      className="fixed bottom-20 md:bottom-6 right-4 left-4 md:left-auto md:max-w-md z-50 bg-slate-900 border border-indigo-500/40 rounded-2xl p-4 shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom-5 duration-300"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0 text-indigo-400 mt-0.5">
            <Sparkles size={18} />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              Update Available
            </h4>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              A new version of ARTHSAVORA is ready with updated financial models, security hardening, and performance improvements.
            </p>
          </div>
        </div>
        <button
          onClick={dismissUpdate}
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Dismiss update notice"
        >
          <X size={16} />
        </button>
      </div>

      <div className="mt-3.5 flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={dismissUpdate} className="text-xs">
          Later
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={applyUpdate}
          className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500"
        >
          <RefreshCw size={13} />
          Update Now
        </Button>
      </div>
    </aside>
  );
};
