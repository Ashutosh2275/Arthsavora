import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Ledger } from '../Ledger';
import { useLedgerStore } from '../../store/useLedgerStore';

vi.mock('../../store/useLedgerStore');

const mockAccounts = [
  {
    id: 'acct-1',
    workspace_id: 'ws-1',
    code: '1010',
    name: 'Operating Cash',
    account_type: 'asset',
    normal_balance: 'debit',
    sub_type: 'cash',
    description: 'Petty cash',
    is_active: true,
    is_system: true,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
  {
    id: 'acct-2',
    workspace_id: 'ws-1',
    code: '4010',
    name: 'Consulting Revenue',
    account_type: 'revenue',
    normal_balance: 'credit',
    sub_type: 'income',
    description: 'Professional billing',
    is_active: true,
    is_system: false,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockJournals = [
  {
    id: 'je-1',
    workspace_id: 'ws-1',
    entry_number: 'JE-202611-0001',
    entry_date: '2026-11-14',
    posting_date: '2026-11-14T06:00:00Z',
    status: 'posted',
    description: 'Customer Consulting Advance',
    source_type: 'manual',
    source_id: null,
    reversal_of_entry_id: null,
    reversal_reason: null,
    accounting_period_id: null,
    created_by: 'user-1',
    posted_by_id: 'user-1',
    metadata: {},
    total_debits: '75000.0000',
    total_credits: '75000.0000',
    is_balanced: true,
    lines: [
      {
        id: 'line-1',
        journal_entry_id: 'je-1',
        ledger_account_id: 'acct-1',
        line_number: 1,
        entry_type: 'debit',
        amount: '75000.0000',
        amount_paise: 7500000,
        currency: 'INR',
        description: 'Debit Cash',
        ledger_account_code: '1010',
        ledger_account_name: 'Operating Cash',
      },
      {
        id: 'line-2',
        journal_entry_id: 'je-1',
        ledger_account_id: 'acct-2',
        line_number: 2,
        entry_type: 'credit',
        amount: '75000.0000',
        amount_paise: 7500000,
        currency: 'INR',
        description: 'Credit Revenue',
        ledger_account_code: '4010',
        ledger_account_name: 'Consulting Revenue',
      },
    ],
    created_at: '2026-11-14T06:00:00Z',
    updated_at: '2026-11-14T06:00:00Z',
  },
];

const mockTrialBalance = {
  as_of_date: '2026-11-14',
  is_balanced: true,
  total_debits: '75000.0000',
  total_credits: '75000.0000',
  total_debits_paise: 7500000,
  total_credits_paise: 7500000,
  difference: '0.0000',
  difference_paise: 0,
  entries: [
    {
      account_id: 'acct-1',
      code: '1010',
      name: 'Operating Cash',
      account_type: 'asset',
      normal_balance: 'debit',
      debit_balance: '75000.0000',
      credit_balance: '0.0000',
      debit_balance_paise: 7500000,
      credit_balance_paise: 0,
    },
    {
      account_id: 'acct-2',
      code: '4010',
      name: 'Consulting Revenue',
      account_type: 'revenue',
      normal_balance: 'credit',
      debit_balance: '0.0000',
      credit_balance: '75000.0000',
      debit_balance_paise: 0,
      credit_balance_paise: 7500000,
    },
  ],
};

describe('Ledger Component', () => {
  const fetchAccountsMock = vi.fn();
  const fetchJournalsMock = vi.fn();
  const fetchTrialBalanceMock = vi.fn();
  const getJournalMock = vi.fn();
  const createJournalMock = vi.fn();
  const postJournalMock = vi.fn();
  const reverseJournalMock = vi.fn();
  const createAccountMock = vi.fn();
  const clearErrorMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useLedgerStore as any).mockReturnValue({
      accounts: mockAccounts,
      journals: mockJournals,
      trialBalance: mockTrialBalance,
      selectedJournal: null,
      totalJournals: 1,
      isLoading: false,
      error: null,
      fetchAccounts: fetchAccountsMock,
      fetchJournals: fetchJournalsMock,
      fetchTrialBalance: fetchTrialBalanceMock,
      getJournal: getJournalMock,
      createJournal: createJournalMock,
      postJournal: postJournalMock,
      reverseJournal: reverseJournalMock,
      createAccount: createAccountMock,
      setSelectedJournal: vi.fn(),
      clearError: clearErrorMock,
    });
  });

  it('renders General Ledger header and navigation tabs', () => {
    render(<Ledger />);
    expect(screen.getByText('General Ledger & Double-Entry Accounting')).toBeInTheDocument();
    expect(screen.getByText('General Journal')).toBeInTheDocument();
    expect(screen.getByText('Chart of Accounts')).toBeInTheDocument();
    expect(screen.getByText('Trial Balance')).toBeInTheDocument();
  });

  it('displays the list of journal entries with status badge and entry number', () => {
    render(<Ledger />);
    expect(screen.getByText('JE-202611-0001')).toBeInTheDocument();
    expect(screen.getByText('Customer Consulting Advance')).toBeInTheDocument();
    expect(screen.getByText('POSTED')).toBeInTheDocument();
  });

  it('switches to Chart of Accounts tab and displays account classifications', () => {
    render(<Ledger />);
    const coaTab = screen.getByText('Chart of Accounts');
    fireEvent.click(coaTab);

    expect(screen.getByText('1010')).toBeInTheDocument();
    expect(screen.getByText('Operating Cash')).toBeInTheDocument();
    expect(screen.getByText('4010')).toBeInTheDocument();
    expect(screen.getByText('Consulting Revenue')).toBeInTheDocument();
  });

  it('switches to Trial Balance tab and verifies balancing equation card', () => {
    render(<Ledger />);
    const tbTab = screen.getByText('Trial Balance');
    fireEvent.click(tbTab);

    expect(fetchTrialBalanceMock).toHaveBeenCalled();
    expect(screen.getByText('✓ EQUATION BALANCED')).toBeInTheDocument();
    expect(screen.getByText('Discrepancy / Difference')).toBeInTheDocument();
  });

  it('opens Record Journal Entry modal when action button is clicked', () => {
    render(<Ledger />);
    const recordBtn = screen.getByText('+ Record Journal Entry');
    fireEvent.click(recordBtn);

    expect(screen.getByText('Record Double-Entry Journal Entry')).toBeInTheDocument();
    expect(screen.getByText('Journal Lines')).toBeInTheDocument();
  });
});
