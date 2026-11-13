import React, { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface StackProps extends HTMLAttributes<HTMLDivElement> {
  direction?: 'row' | 'col';
  spacing?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  align?: 'start' | 'center' | 'end' | 'stretch';
  justify?: 'start' | 'center' | 'end' | 'between' | 'around';
  wrap?: boolean;
}

export const Stack = forwardRef<HTMLDivElement, StackProps>(
  (
    {
      className,
      direction = 'col',
      spacing = 'md',
      align = 'stretch',
      justify = 'start',
      wrap = false,
      children,
      ...props
    },
    ref
  ) => {
    const directionClasses = {
      row: 'flex-row',
      col: 'flex-col',
    };

    const spacingClasses = {
      none: 'gap-0',
      xs: 'gap-1',
      sm: 'gap-2',
      md: 'gap-4',
      lg: 'gap-6',
      xl: 'gap-8',
    };

    const alignClasses = {
      start: 'items-start',
      center: 'items-center',
      end: 'items-end',
      stretch: 'items-stretch',
    };

    const justifyClasses = {
      start: 'justify-start',
      center: 'justify-center',
      end: 'justify-end',
      between: 'justify-between',
      around: 'justify-around',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'flex',
          directionClasses[direction],
          spacingClasses[spacing],
          alignClasses[align],
          justifyClasses[justify],
          wrap && 'flex-wrap',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Stack.displayName = 'Stack';
