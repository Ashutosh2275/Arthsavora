import React, { type InputHTMLAttributes, forwardRef } from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  helperText?: string;
  error?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, helperText, error, id, disabled, checked, ...props }, ref) => {
    const generatedId = React.useId();
    const checkboxId = id || generatedId;
    const errorId = `${checkboxId}-error`;
    const helperId = `${checkboxId}-helper`;

    return (
      <div className="flex flex-col space-y-1">
        <label
          htmlFor={checkboxId}
          className={cn(
            'inline-flex items-start gap-3 cursor-pointer select-none text-sm text-slate-200',
            disabled && 'cursor-not-allowed opacity-50'
          )}
        >
          <div className="relative flex items-center justify-center mt-0.5">
            <input
              id={checkboxId}
              type="checkbox"
              ref={ref}
              disabled={disabled}
              checked={checked}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? errorId : helperText ? helperId : undefined}
              className="peer sr-only"
              {...props}
            />
            <div
              className={cn(
                'h-4 w-4 rounded border border-slate-700 bg-slate-900 transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-slate-900 peer-checked:border-indigo-600 peer-checked:bg-indigo-600',
                error && 'border-rose-500',
                className
              )}
            >
              <Check className="h-3 w-3 text-white opacity-0 transition-opacity peer-checked:opacity-100" />
            </div>
          </div>
          {label && <span className="text-sm font-medium leading-none">{label}</span>}
        </label>
        {error && (
          <p id={errorId} className="pl-7 text-xs font-medium text-rose-400" role="alert">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={helperId} className="pl-7 text-xs text-slate-400">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';
