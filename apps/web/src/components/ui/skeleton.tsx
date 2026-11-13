import React, { type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn('animate-pulse rounded-lg bg-slate-800/70', className)}
      {...props}
    />
  );
}
