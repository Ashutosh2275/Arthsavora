import React, { type InputHTMLAttributes, forwardRef, useState } from 'react';
import { Eye, EyeOff, Search, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isPasswordToggle?: boolean;
  onClear?: () => void;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      helperText,
      error,
      type = 'text',
      id,
      leftIcon,
      rightIcon,
      isPasswordToggle = false,
      onClear,
      disabled,
      value,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const generatedId = React.useId();
    const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, '-')}` : generatedId);
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    const isPassword = type === 'password' || isPasswordToggle;
    const computedType = isPassword ? (showPassword ? 'text' : 'password') : type;
    const isSearch = type === 'search';

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-semibold uppercase tracking-wider text-slate-400"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {/* Left Icon or Search icon */}
          {leftIcon ? (
            <span className="pointer-events-none absolute left-3 flex items-center text-slate-400">
              {leftIcon}
            </span>
          ) : isSearch ? (
            <span className="pointer-events-none absolute left-3 flex items-center text-slate-400">
              <Search className="h-4 w-4" aria-hidden="true" />
            </span>
          ) : null}

          <input
            id={inputId}
            type={computedType}
            ref={ref}
            disabled={disabled}
            value={value}
            aria-invalid={Boolean(error)}
            aria-describedby={
              error ? errorId : helperText ? helperId : undefined
            }
            className={cn(
              'w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50',
              (leftIcon || isSearch) && 'pl-9',
              (rightIcon || isPassword || (isSearch && onClear && value)) && 'pr-9',
              error && 'border-rose-500 focus:border-rose-500 focus:ring-rose-500/20',
              className
            )}
            {...props}
          />

          {/* Right Icon / Password Toggle / Search Clear */}
          {isPassword ? (
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-3 text-slate-400 hover:text-slate-200 focus:outline-none"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          ) : isSearch && onClear && value ? (
            <button
              type="button"
              onClick={onClear}
              aria-label="Clear search"
              className="absolute right-3 text-slate-400 hover:text-slate-200 focus:outline-none"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : rightIcon ? (
            <span className="pointer-events-none absolute right-3 flex items-center text-slate-400">
              {rightIcon}
            </span>
          ) : null}
        </div>

        {error && (
          <p id={errorId} className="text-xs font-medium text-rose-400" role="alert">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="text-xs text-slate-400">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
