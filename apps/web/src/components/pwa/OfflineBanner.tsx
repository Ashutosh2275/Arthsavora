import React from 'react';
import { WifiOff, Wifi, AlertTriangle } from 'lucide-react';
import { usePwaStore } from '@/pwa/usePwaStore';

export const OfflineBanner: React.FC = () => {
  const isOffline = usePwaStore((state) => state.isOffline);
  const wasOffline = usePwaStore((state) => state.wasOffline);

  if (!isOffline && !wasOffline) {
    return null;
  }

  if (wasOffline) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="w-full bg-emerald-600 text-white px-4 py-2 text-xs font-medium flex items-center justify-center gap-2 shadow-sm animate-in fade-in duration-300"
      >
        <Wifi size={14} className="shrink-0" />
        <span>Network connection restored. Real-time ledger synchronization active.</span>
      </div>
    );
  }

  return (
    <aside
      role="alert"
      aria-live="assertive"
      className="w-full bg-amber-500/15 border-b border-amber-500/30 text-amber-200 px-4 py-2 text-xs flex items-center justify-between gap-3 shadow-inner"
    >
      <div className="flex items-center gap-2">
        <WifiOff size={15} className="text-amber-400 shrink-0" />
        <div>
          <span className="font-semibold text-amber-300">Offline Mode:</span>{' '}
          <span>
            Viewing cached application shell. Financial transactions and reports require an active, secure connection.
          </span>
        </div>
      </div>
      <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-amber-300/80 bg-amber-500/20 px-2 py-0.5 rounded border border-amber-500/30 shrink-0">
        <AlertTriangle size={12} />
        <span>Read-Only</span>
      </div>
    </aside>
  );
};
