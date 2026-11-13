import React from 'react';
import { cn } from '@/lib/utils';

export interface DividerProps {
  orientation?: 'horizontal' | 'vertical';
  label?: string;
  className?: string;
}

export const Divider: React.FC<DividerProps> = ({
  orientation = 'horizontal',
  label,
  className,
}) => {
  if (orientation === 'vertical') {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn('h-full w-px bg-slate-800', className)}
      />
    );
  }

  if (label) {
    return (
      <div
        role="separator"
        aria-orientation="horizontal"
        className={cn('relative my-4 flex items-center', className)}
      >
        <div className="flex-grow border-t border-slate-800" />
        <span className="mx-3 shrink text-xs uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <div className="flex-grow border-t border-slate-800" />
      </div>
    );
  }

  return (
    <hr
      role="separator"
      aria-orientation="horizontal"
      className={cn('my-4 border-0 border-t border-slate-800', className)}
    />
  );
};
