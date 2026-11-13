import React from 'react';
import {
  Clock,
  CheckCircle2,
  ShieldCheck,
  XCircle,
  Ban,
  Lock,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type TransactionStatus = 'pending' | 'cleared' | 'reconciled' | 'failed' | 'cancelled';
export type AccountStatus = 'active' | 'frozen' | 'closed';

export interface StatusBadgeProps {
  status: TransactionStatus | AccountStatus | string;
  isAiPredicted?: boolean;
  confidenceScore?: number; // 0 to 1 or 0 to 100
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  isAiPredicted = false,
  confidenceScore,
  size = 'md',
  className,
}) => {
  const normalized = status.toLowerCase();

  const configs: Record<
    string,
    { label: string; icon: React.ReactNode; container: string }
  > = {
    pending: {
      label: 'Pending',
      icon: <Clock className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />,
      container: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
    },
    cleared: {
      label: 'Cleared',
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />,
      container: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    },
    reconciled: {
      label: 'Reconciled',
      icon: <ShieldCheck className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />,
      container: 'border-sky-500/20 bg-sky-500/10 text-sky-300',
    },
    failed: {
      label: 'Failed',
      icon: <XCircle className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />,
      container: 'border-rose-500/20 bg-rose-500/10 text-rose-300',
    },
    cancelled: {
      label: 'Cancelled',
      icon: <Ban className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />,
      container: 'border-slate-700 bg-slate-800 text-slate-300',
    },
    active: {
      label: 'Active',
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />,
      container: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    },
    frozen: {
      label: 'Frozen',
      icon: <Lock className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />,
      container: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
    },
    closed: {
      label: 'Closed',
      icon: <Ban className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />,
      container: 'border-slate-700 bg-slate-800 text-slate-400',
    },
  };

  const current = configs[normalized] || {
    label: status.toUpperCase(),
    icon: <Clock className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />,
    container: 'border-slate-700 bg-slate-800 text-slate-300',
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  const formattedConfidence =
    confidenceScore !== undefined
      ? confidenceScore > 1
        ? `${Math.round(confidenceScore)}%`
        : `${Math.round(confidenceScore * 100)}%`
      : null;

  return (
    <div className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          'inline-flex items-center font-medium rounded-md border select-none',
          current.container,
          sizeClasses[size],
          className
        )}
      >
        {current.icon}
        <span>{current.label}</span>
      </span>

      {isAiPredicted && (
        <span
          title={
            formattedConfidence
              ? `AI predicted with ${formattedConfidence} confidence`
              : 'AI predicted transaction'
          }
          className="inline-flex items-center gap-1 rounded-md border border-indigo-500/30 bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-300"
        >
          <Sparkles className="h-3 w-3 text-indigo-400" aria-hidden="true" />
          <span>AI{formattedConfidence ? ` (${formattedConfidence})` : ''}</span>
        </span>
      )}
    </div>
  );
};
