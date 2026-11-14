import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Accounts from '../Accounts';
import useAccountStore from '@/store/useAccountStore';

// Mock zustand store
vi.mock('@/store/useAccountStore');

const mockAccounts = [
  {
    id: 'acc-1',
    workspace_id: 'ws-1',
    name: 'HDFC Salary Savings',
    account_type: 'savings',
    currency: 'INR',
    institution_name: 'HDFC Bank',
    masked_identifier: 'XX4321',
    status: 'active',
    current_book_balance: '125000.50',
    current_book_balance_paise: 12500050,
    available_balance: '125000.50',
    available_balance_paise: 12500050,
    pending_amount: '0.00',
    pending_amount_paise: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    balances: {
      currency: 'INR',
      book_balance: '125000.50',
      book_balance_paise: 12500050,
      available_balance: '125000.50',
      available_balance_paise: 12500050,
      pending_amount: '0.00',
      pending_amount_paise: 0,
      opening_balance: '50000.00',
      opening_balance_paise: 5000000,
    },
  },
  {
    id: 'acc-2',
    workspace_id: 'ws-1',
    name: 'Amazon ICICI Credit Card',
    account_type: 'credit_card',
    currency: 'INR',
    institution_name: 'ICICI Bank',
    masked_identifier: 'XX2040',
    status: 'active',
    current_book_balance: '0.00',
    current_book_balance_paise: 0,
    outstanding_liability: '14200.00',
    outstanding_liability_paise: 1420000,
    pending_amount: '0.00',
    pending_amount_paise: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    balances: {
      currency: 'INR',
      book_balance: '0.00',
      book_balance_paise: 0,
      outstanding_liability: '14200.00',
      outstanding_liability_paise: 1420000,
      credit_limit: '250000.00',
      credit_limit_paise: 25000000,
      available_credit: '235800.00',
      available_credit_paise: 23580000,
      due_date: '2026-04-12',
      pending_amount: '0.00',
      pending_amount_paise: 0,
      opening_balance: '0.00',
      opening_balance_paise: 0,
    },
  },
];

describe('Accounts Page Component', () => {
  const mockFetchAccounts = vi.fn();
  const mockCreateAccount = vi.fn();
  const mockArchiveAccount = vi.fn();
  const mockRestoreAccount = vi.fn();
  const mockCloseAccount = vi.fn();
  const mockFetchBalanceHistory = vi.fn();
  const mockRecordSnapshot = vi.fn();
  const mockSetSelectedAccount = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAccountStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      accounts: mockAccounts,
      selectedAccount: null,
      balanceHistory: [],
      loading: false,
      historyLoading: false,
      fetchAccounts: mockFetchAccounts,
      setSelectedAccount: mockSetSelectedAccount,
      createAccount: mockCreateAccount,
      archiveAccount: mockArchiveAccount,
      restoreAccount: mockRestoreAccount,
      closeAccount: mockCloseAccount,
      fetchBalanceHistory: mockFetchBalanceHistory,
      recordSnapshot: mockRecordSnapshot,
    });
  });

  it('renders page header and summary KPI metrics', () => {
    render(<Accounts />);
    expect(screen.getByRole('heading', { level: 1, name: /financial accounts/i })).toBeInTheDocument();
    expect(screen.getByText(/liquid assets/i)).toBeInTheDocument();
    expect(screen.getByText(/total liabilities/i)).toBeInTheDocument();
    expect(screen.getByText(/total credit limit/i)).toBeInTheDocument();
    expect(screen.getByText(/active accounts/i)).toBeInTheDocument();
    expect(mockFetchAccounts).toHaveBeenCalledTimes(1);
  });

  it('renders mapped financial account cards with details', () => {
    render(<Accounts />);
    expect(screen.getByText('HDFC Salary Savings')).toBeInTheDocument();
    expect(screen.getByText('Amazon ICICI Credit Card')).toBeInTheDocument();
    expect(screen.getByText('XX4321')).toBeInTheDocument();
    expect(screen.getByText('XX2040')).toBeInTheDocument();
  });

  it('opens Add Account modal when clicking Add Account button', () => {
    render(<Accounts />);
    const addButtons = screen.getAllByRole('button', { name: /add account/i });
    fireEvent.click(addButtons[0]);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Add Financial Account')).toBeInTheDocument();
  });

  it('filters account cards when switching tabs', () => {
    render(<Accounts />);
    const creditCardsTab = screen.getByRole('button', { name: /credit cards/i });
    fireEvent.click(creditCardsTab);
    expect(screen.getByText('Amazon ICICI Credit Card')).toBeInTheDocument();
    expect(screen.queryByText('HDFC Salary Savings')).not.toBeInTheDocument();
  });
});
