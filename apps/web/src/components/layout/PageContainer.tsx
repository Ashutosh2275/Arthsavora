import React, { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface PageContainerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'default' | 'narrow' | 'wide' | 'full';
}

export const PageContainer = forwardRef<HTMLDivElement, PageContainerProps>(
  ({ className, size = 'default', children, ...props }, ref) => {
    const sizeClasses = {
      narrow: 'max-w-4xl',
      default: 'max-w-7xl',
      wide: 'max-w-8xl',
      full: 'max-w-full',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8',
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

PageContainer.displayName = 'PageContainer';
