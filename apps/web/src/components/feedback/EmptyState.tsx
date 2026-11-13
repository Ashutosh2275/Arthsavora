import React, { type ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 px-6 py-16 text-center">
      <div className="mb-4 rounded-2xl bg-slate-800/50 p-4 text-slate-500">
        {icon || <Inbox size={32} />}
      </div>
      <h4 className="text-base font-bold text-slate-200">{title}</h4>
      <p className="mt-1 max-w-sm text-xs text-slate-400">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
