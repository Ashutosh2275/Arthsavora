import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

export interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  onDismiss?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  onDismiss,
  className,
}) => {
  const variantConfig = {
    info: {
      container: 'border-sky-800/60 bg-sky-950/30 text-sky-200',
      icon: <Info className="h-5 w-5 text-sky-400 shrink-0 mt-0.5" aria-hidden="true" />,
      titleColor: 'text-sky-300 font-semibold',
    },
    success: {
      container: 'border-emerald-800/60 bg-emerald-950/30 text-emerald-200',
      icon: <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />,
      titleColor: 'text-emerald-300 font-semibold',
    },
    warning: {
      container: 'border-amber-800/60 bg-amber-950/30 text-amber-200',
      icon: <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />,
      titleColor: 'text-amber-300 font-semibold',
    },
    error: {
      container: 'border-rose-800/60 bg-rose-950/30 text-rose-200',
      icon: <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" aria-hidden="true" />,
      titleColor: 'text-rose-300 font-semibold',
    },
  };

  const current = variantConfig[variant];

  return (
    <div
      role="alert"
      className={cn(
        'relative flex items-start gap-3 rounded-xl border p-4 text-sm',
        current.container,
        className
      )}
    >
      {current.icon}
      <div className="flex-1 space-y-1">
        {title && <h5 className={current.titleColor}>{title}</h5>}
        <div className="text-sm opacity-90 leading-relaxed">{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss alert"
          className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
};
