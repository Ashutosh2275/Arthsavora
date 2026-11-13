import React from 'react';
import { formatINR } from '@arthsavora/utilities';
import { cn } from '@/lib/utils';

export interface FinancialAmountProps {
  amount: number; // in Rupees
  currency?: string;
  type?: 'income' | 'expense' | 'neutral' | 'auto';
  showSign?: boolean;
  isPrivate?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  className?: string;
}

export const FinancialAmount: React.FC<FinancialAmountProps> = ({
  amount,
  type = 'auto',
  showSign = false,
  isPrivate = false,
  size = 'md',
  className,
}) => {
  if (isPrivate) {
    return (
      <span
        aria-label="Private financial figure"
        className={cn('tabular-nums font-mono font-semibold tracking-wider text-slate-400 select-none', className)}
      >
        ••••••
      </span>
    );
  }

  // Determine effective financial type
  let effectiveType = type;
  if (type === 'auto') {
    if (amount > 0) effectiveType = 'income';
    else if (amount < 0) effectiveType = 'expense';
    else effectiveType = 'neutral';
  }

  const absAmount = Math.abs(amount);
  const formattedString = formatINR(absAmount);

  // Sign indicator
  let signPrefix = '';
  if (showSign) {
    if (amount > 0 || type === 'income') signPrefix = '+';
    else if (amount < 0 || type === 'expense') signPrefix = '-';
  }

  const colorStyles = {
    income: 'text-emerald-400 font-semibold',
    expense: 'text-rose-400 font-semibold',
    neutral: 'text-slate-100 font-medium',
    auto: 'text-slate-100 font-medium',
  };

  const sizeStyles = {
    xs: 'text-xs',
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-2xl font-bold',
    '2xl': 'text-3xl sm:text-4xl font-extrabold',
  };

  return (
    <span
      className={cn(
        'tabular-nums font-mono inline-flex items-baseline tracking-tight',
        colorStyles[effectiveType],
        sizeStyles[size],
        className
      )}
    >
      {signPrefix}
      {formattedString}
    </span>
  );
};
