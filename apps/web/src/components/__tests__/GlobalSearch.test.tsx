import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { GlobalSearch } from '../layout/GlobalSearch';
import useAccountStore from '@/store/useAccountStore';
import useTransactionStore from '@/store/useTransactionStore';
import { useBudgetStore } from '@/store/useBudgetStore';
import { useGoalStore } from '@/store/useGoalStore';
import { useBusinessStore } from '@/store/useBusinessStore';
import { useDocumentStore } from '@/store/useDocumentStore';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/store/useAccountStore');
vi.mock('@/store/useTransactionStore');
vi.mock('@/store/useBudgetStore');
vi.mock('@/store/useGoalStore');
vi.mock('@/store/useBusinessStore');
vi.mock('@/store/useDocumentStore');

describe('GlobalSearch Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAccountStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      accounts: [
        { id: 'acc-1', name: 'HDFC Salary Account', institution_name: 'HDFC Bank', current_book_balance_paise: 25000000 },
      ],
    });
    (useTransactionStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      transactions: [
        { id: 'tx-1', description: 'Amazon Cloud AWS', merchant_name: 'AWS India', amount_paise: 500000 },
      ],
    });
    (useBudgetStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      budgets: [{ id: 'bud-1', name: 'Software & Infrastructure', limit_paise: 1000000 }],
    });
    (useGoalStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      goals: [{ id: 'goal-1', name: 'Emergency Reserve Fund', target_paise: 50000000 }],
    });
    (useBusinessStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      invoices: [{ id: 'inv-1', invoice_number: 'INV-2026-001', client_name: 'Starlight Tech', total_amount_paise: 11800000 }],
    });
    (useDocumentStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      documents: [{ id: 'doc-1', filename: 'flight_ticket.pdf', extracted_merchant: 'IndiGo Airlines', status: 'completed' }],
    });
  });

  it('renders search trigger button with shortcut indicator', () => {
    render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
    expect(screen.getByRole('button', { name: /search financial records/i })).toBeInTheDocument();
    expect(screen.getByText('Search records...')).toBeInTheDocument();
  });

  it('opens search dialog when trigger button is clicked', () => {
    render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
    const trigger = screen.getByRole('button', { name: /search financial records/i });
    fireEvent.click(trigger);

    expect(screen.getByRole('dialog', { name: /global financial search/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search transactions, accounts, invoices/i)).toBeInTheDocument();
  });

  it('filters results dynamically based on typed query', () => {
    render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByRole('button', { name: /search financial records/i }));

    const input = screen.getByPlaceholderText(/search transactions, accounts, invoices/i);
    fireEvent.change(input, { target: { value: 'HDFC' } });

    expect(screen.getByText('HDFC Salary Account')).toBeInTheDocument();
    expect(screen.getByText(/HDFC Bank/i)).toBeInTheDocument();
  });

  it('navigates to target resource when an item is selected', () => {
    render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByRole('button', { name: /search financial records/i }));

    const input = screen.getByPlaceholderText(/search transactions, accounts, invoices/i);
    fireEvent.change(input, { target: { value: 'AWS' } });

    const txItem = screen.getByText('AWS India');
    fireEvent.click(txItem);

    expect(mockNavigate).toHaveBeenCalledWith('/transactions');
  });

  it('closes dialog when Escape key is pressed', () => {
    render(
      <BrowserRouter>
        <GlobalSearch />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByRole('button', { name: /search financial records/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
