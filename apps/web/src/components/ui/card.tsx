import React, { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'subtle';
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const base = 'rounded-2xl transition-all';
    const variants = {
      default: 'bg-slate-900/60 border border-slate-800 p-6',
      elevated: 'bg-slate-900 border border-slate-800 p-6 shadow-xl',
      subtle: 'bg-slate-900/30 border border-slate-800/50 p-5',
    };

    return (
      <div
        ref={ref}
        className={cn(base, variants[variant], className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
