import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Transactions from '../Transactions';
import useTransactionStore from '@/store/useTransactionStore';
import useAccountStore from '@/store/useAccountStore';

// Mock zustand stores
vi.mock('@/store/useTransactionStore');
vi.mock('@/store/useAccountStore');

const mockTransactions = [
  {
    id: 'tx-1',
    workspace_id: 'ws-1',
    account_id: 'acc-1',
    amount: '45000.50',
    amount_paise: 4500050,
    currency: 'INR',
    transaction_type: 'income',
    direction: 'inflow',
    transaction_date: '2026-03-15',
    description: 'Software Consulting Retainer',
    merchant_name: 'Tech Corp',
    category_id: null,
    status: 'posted',
    source_type: 'manual',
    is_ai_predicted: true,
    ai_confidence: 0.92,
    source_provenance: {},
    metadata: {},
    created_at: '2026-03-15T10:00:00Z',
    updated_at: '2026-03-15T10:00:00Z',
  },
  {
    id: 'tx-2',
    workspace_id: 'ws-1',
    account_id: 'acc-1',
    amount: '1250.00',
    amount_paise: 125000,
    currency: 'INR',
    transaction_type: 'expense',
    direction: 'outflow',
    transaction_date: '2026-03-16',
    description: 'Office Snacks',
    merchant_name: 'Blinkit',
    category_id: null,
    status: 'pending',
    source_type: 'manual',
    is_ai_predicted: false,
    ai_confidence: null,
    source_provenance: {},
    metadata: {},
    created_at: '2026-03-16T12:00:00Z',
    updated_at: '2026-03-16T12:00:00Z',
  },
];

const mockAccounts = [
  {
    id: 'acc-1',
    name: 'HDFC Current',
    account_type: 'current',
    currency: 'INR',
    current_book_balance: '150000.00',
    current_book_balance_paise: 15000000,
  },
];

describe('Transactions Page', () => {
  const mockFetchTransactions = vi.fn();
  const mockFetchAccounts = vi.fn();
  const mockCreateTransaction = vi.fn();
  const mockCreateTransfer = vi.fn();
  const mockPostTransaction = vi.fn();
  const mockCancelTransaction = vi.fn();
  const mockReverseTransaction = vi.fn();
  const mockRefundTransaction = vi.fn();
  const mockFetchHistory = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useAccountStore).mockReturnValue({
      accounts: mockAccounts,
      fetchAccounts: mockFetchAccounts,
    } as any);

    vi.mocked(useTransactionStore).mockReturnValue({
      transactions: mockTransactions,
      total: 2,
      page: 1,
      pageSize: 20,
      loading: false,
      historyLoading: false,
      activeHistory: [],
      selectedTransaction: null,
      fetchTransactions: mockFetchTransactions,
      createTransaction: mockCreateTransaction,
      createTransfer: mockCreateTransfer,
      postTransaction: mockPostTransaction,
      cancelTransaction: mockCancelTransaction,
      reverseTransaction: mockReverseTransaction,
      refundTransaction: mockRefundTransaction,
      fetchHistory: mockFetchHistory,
    } as any);
  });

  it('renders page header and transactions list correctly', () => {
    render(<Transactions />);

    expect(screen.getByText('Financial Transactions')).toBeInTheDocument();
    expect(screen.getByText('Software Consulting Retainer')).toBeInTheDocument();
    expect(screen.getByText('Office Snacks')).toBeInTheDocument();
    expect(screen.getByText('Tech Corp')).toBeInTheDocument();
    expect(screen.getByText('Blinkit')).toBeInTheDocument();
  });

  it('displays transaction status badges properly', () => {
    render(<Transactions />);

    expect(screen.getAllByText('Posted').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0);
  });

  it('opens new transaction modal when button clicked', () => {
    render(<Transactions />);

    const newTxBtn = screen.getByRole('button', { name: /new transaction/i });
    fireEvent.click(newTxBtn);

    expect(screen.getByText('Record Financial Transaction')).toBeInTheDocument();
    expect(screen.getByLabelText(/narrative/i)).toBeInTheDocument();
  });

  it('opens transfer modal when transfer button clicked', () => {
    render(<Transactions />);

    const xferBtn = screen.getByRole('button', { name: /transfer/i });
    fireEvent.click(xferBtn);

    expect(screen.getByText('Execute Internal Account Transfer')).toBeInTheDocument();
  });
});
