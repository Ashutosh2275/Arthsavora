import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PercentageDisplayProps {
  value: number; // e.g. 5.4 for +5.4%
  showArrow?: boolean;
  invertColors?: boolean; // When an increase in expense is bad
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

export const PercentageDisplay: React.FC<PercentageDisplayProps> = ({
  value,
  showArrow = true,
  invertColors = false,
  size = 'sm',
  className,
}) => {
  const isPositive = value > 0;
  const isZero = value === 0;

  // For expenses, an increase is negative (rose)
  const isGood = invertColors ? !isPositive : isPositive;

  const colorClass = isZero
    ? 'text-slate-400'
    : isGood
    ? 'text-emerald-400'
    : 'text-rose-400';

  const sizeClasses = {
    xs: 'text-xs gap-0.5',
    sm: 'text-sm gap-1',
    md: 'text-base gap-1.5',
    lg: 'text-lg gap-2 font-semibold',
  };

  const iconSizes = {
    xs: 'h-3 w-3',
    sm: 'h-3.5 w-3.5',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  const formatted = `${isPositive ? '+' : ''}${value.toFixed(1)}%`;

  return (
    <span
      className={cn(
        'tabular-nums font-mono inline-flex items-center font-medium select-none',
        colorClass,
        sizeClasses[size],
        className
      )}
    >
      {showArrow && (
        isZero ? (
          <Minus className={iconSizes[size]} aria-hidden="true" />
        ) : isPositive ? (
          <ArrowUpRight className={iconSizes[size]} aria-hidden="true" />
        ) : (
          <ArrowDownRight className={iconSizes[size]} aria-hidden="true" />
        )
      )}
      <span>{formatted}</span>
    </span>
  );
};
