import React, { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  cols?: 1 | 2 | 3 | 4 | 6 | 12;
  gap?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
}

export const Grid = forwardRef<HTMLDivElement, GridProps>(
  ({ className, cols = 3, gap = 'md', children, ...props }, ref) => {
    const colClasses = {
      1: 'grid-cols-1',
      2: 'grid-cols-1 sm:grid-cols-2',
      3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
      4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
      6: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6',
      12: 'grid-cols-12',
    };

    const gapClasses = {
      none: 'gap-0',
      sm: 'gap-3',
      md: 'gap-5',
      lg: 'gap-6',
      xl: 'gap-8',
    };

    return (
      <div
        ref={ref}
        className={cn('grid', colClasses[cols], gapClasses[gap], className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Grid.displayName = 'Grid';
