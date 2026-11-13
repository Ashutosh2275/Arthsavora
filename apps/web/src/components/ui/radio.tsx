import React, { type InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface RadioOption {
  value: string;
  label: string;
  helperText?: string;
  disabled?: boolean;
}

export interface RadioGroupProps {
  name: string;
  options: RadioOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  label?: string;
  error?: string;
  className?: string;
}

export const RadioGroup: React.FC<RadioGroupProps> = ({
  name,
  options,
  value,
  defaultValue,
  onChange,
  label,
  error,
  className,
}) => {
  const [internalValue, setInternalValue] = React.useState(defaultValue || '');
  const currentValue = value !== undefined ? value : internalValue;

  const handleChange = (val: string) => {
    if (value === undefined) setInternalValue(val);
    onChange?.(val);
  };

  return (
    <div className={cn('space-y-2', className)} role="radiogroup" aria-label={label}>
      {label && (
        <span className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </span>
      )}
      <div className="space-y-2">
        {options.map((option) => {
          const isSelected = currentValue === option.value;
          return (
            <label
              key={option.value}
              className={cn(
                'flex items-start gap-3 cursor-pointer select-none rounded-lg border border-slate-800 bg-slate-900/40 p-3 transition-colors hover:border-slate-700',
                isSelected && 'border-indigo-600 bg-indigo-950/20',
                option.disabled && 'cursor-not-allowed opacity-50'
              )}
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={isSelected}
                disabled={option.disabled}
                onChange={() => handleChange(option.value)}
                className="mt-0.5 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-700 bg-slate-900"
              />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-100">{option.label}</span>
                {option.helperText && (
                  <span className="text-xs text-slate-400 mt-0.5">{option.helperText}</span>
                )}
              </div>
            </label>
          );
        })}
      </div>
      {error && <p className="text-xs font-medium text-rose-400" role="alert">{error}</p>}
    </div>
  );
};

export interface RadioProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ className, label, id, ...props }, ref) => {
    const generatedId = React.useId();
    const radioId = id || generatedId;

    return (
      <label htmlFor={radioId} className="inline-flex items-center gap-2 cursor-pointer select-none">
        <input
          id={radioId}
          type="radio"
          ref={ref}
          className={cn(
            'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-slate-700 bg-slate-900',
            className
          )}
          {...props}
        />
        {label && <span className="text-sm text-slate-200">{label}</span>}
      </label>
    );
  }
);

Radio.displayName = 'Radio';
