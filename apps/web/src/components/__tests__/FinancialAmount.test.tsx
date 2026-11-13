import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { FinancialAmount } from '../ui/financial-amount';

describe('FinancialAmount Component', () => {
  it('formats positive INR amount with tabular numbers and emerald styling', () => {
    render(<FinancialAmount amount={150000} type="income" showSign />);
    const el = screen.getByText('+₹1,50,000.00');
    expect(el).toBeInTheDocument();
    expect(el.className).toContain('text-emerald-400');
    expect(el.className).toContain('tabular-nums');
  });

  it('formats negative/expense INR amount with rose styling', () => {
    render(<FinancialAmount amount={-4250.5} showSign />);
    const el = screen.getByText('-₹4,250.50');
    expect(el).toBeInTheDocument();
    expect(el.className).toContain('text-rose-400');
  });

  it('renders privacy masked bullets when isPrivate is true', () => {
    render(<FinancialAmount amount={1000000} isPrivate />);
    const el = screen.getByLabelText(/private financial figure/i);
    expect(el).toHaveTextContent('••••••');
  });
});
