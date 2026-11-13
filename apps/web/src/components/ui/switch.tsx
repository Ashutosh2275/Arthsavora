import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface SwitchProps {
  id?: string;
  label?: string;
  helperText?: string;
  checked?: boolean;
  defaultChecked?: boolean;
  disabled?: boolean;
  onChange?: (checked: boolean) => void;
  className?: string;
}

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  (
    {
      id,
      label,
      helperText,
      checked,
      defaultChecked = false,
      disabled = false,
      onChange,
      className,
    },
    ref
  ) => {
    const [isChecked, setIsChecked] = React.useState(defaultChecked);
    const isControlled = checked !== undefined;
    const currentChecked = isControlled ? checked : isChecked;

    const generatedId = React.useId();
    const switchId = id || generatedId;
    const helperId = `${switchId}-helper`;

    const handleToggle = () => {
      if (disabled) return;
      const next = !currentChecked;
      if (!isControlled) {
        setIsChecked(next);
      }
      onChange?.(next);
    };

    return (
      <div className="flex items-center justify-between gap-4">
        {(label || helperText) && (
          <div className="flex flex-col">
            {label && (
              <label
                htmlFor={switchId}
                className={cn(
                  'text-sm font-medium text-slate-200 cursor-pointer',
                  disabled && 'cursor-not-allowed opacity-50'
                )}
              >
                {label}
              </label>
            )}
            {helperText && (
              <span id={helperId} className="text-xs text-slate-400">
                {helperText}
              </span>
            )}
          </div>
        )}
        <button
          id={switchId}
          ref={ref}
          type="button"
          role="switch"
          aria-checked={currentChecked}
          aria-describedby={helperText ? helperId : undefined}
          disabled={disabled}
          onClick={handleToggle}
          className={cn(
            'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-50',
            currentChecked ? 'bg-indigo-600' : 'bg-slate-700',
            className
          )}
        >
          <span
            className={cn(
              'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out',
              currentChecked ? 'translate-x-5' : 'translate-x-0'
            )}
          />
        </button>
      </div>
    );
  }
);

Switch.displayName = 'Switch';
