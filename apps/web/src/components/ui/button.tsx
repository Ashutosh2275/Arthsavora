import React, { type ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  loadingText?: string;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      loadingText = 'Processing...',
      type = 'button',
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:pointer-events-none disabled:opacity-50 select-none';

    // Map danger alias to destructive
    const effectiveVariant = variant === 'danger' ? 'destructive' : variant;

    const variants: Record<string, string> = {
      primary:
        'bg-indigo-600 text-white hover:bg-indigo-500 active:bg-indigo-700 shadow-sm shadow-indigo-600/30',
      secondary:
        'bg-slate-800 text-slate-100 hover:bg-slate-700 active:bg-slate-900 border border-slate-700/80',
      outline:
        'border border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white active:bg-slate-850',
      ghost:
        'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 active:bg-slate-800',
      destructive:
        'bg-rose-600 text-white hover:bg-rose-500 active:bg-rose-700 shadow-sm shadow-rose-600/30',
    };

    const sizes: Record<string, string> = {
      sm: 'h-8 px-3 text-xs rounded-md gap-1.5',
      md: 'h-10 px-4 text-sm rounded-lg gap-2',
      lg: 'h-12 px-6 text-base rounded-xl gap-2.5',
      icon: 'h-10 w-10 p-0 rounded-lg',
    };

    const isButtonDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        type={type}
        className={cn(baseStyles, variants[effectiveVariant], sizes[size], className)}
        disabled={isButtonDisabled}
        aria-busy={isLoading}
        aria-disabled={isButtonDisabled}
        {...props}
      >
        {isLoading ? (
          <span className="inline-flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin text-current"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            {size !== 'icon' && <span>{loadingText}</span>}
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
