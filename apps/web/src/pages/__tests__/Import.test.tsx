import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Import } from '../Import';
import { useImportStore } from '../../store/useImportStore';
import { useAccountStore } from '../../store/useAccountStore';

vi.mock('../../store/useImportStore');
vi.mock('../../store/useAccountStore');

const mockAccounts = [
  {
    id: 'acct-hdfc',
    name: 'HDFC Current Account',
    account_type: 'current',
    currency: 'INR',
    current_book_balance: '150000.0000',
    available_balance: '150000.0000',
    status: 'active',
  },
];

const mockUploadResult = {
  job_id: 'job-123',
  batch_id: 'batch-456',
  status: 'awaiting_review',
  source_type: 'csv',
  original_filename: 'hdfc_nov_statement.csv',
  total_records: 3,
  valid_records: 2,
  invalid_records: 1,
  duplicate_records: 1,
  available_sheets: [],
  reconciliation: {
    opening_balance: '100000.0000',
    closing_balance: '125000.0000',
    calculated_closing_balance: '125000.0000',
    difference: '0.0000',
    is_reconciled: true,
  },
  candidates_preview: [],
};

const mockCandidates = [
  {
    id: 'cand-1',
    import_batch_id: 'batch-456',
    workspace_id: 'ws-1',
    account_id: 'acct-hdfc',
    source_row_number: 1,
    raw_data: { Date: '14/11/2026', Narration: 'Salary Credit', Deposit: '50000.00' },
    normalized_data: {
      transaction_date: '2026-11-14',
      description: 'Salary Credit Corp Payroll',
      amount: '50000.0000',
      amount_paise: 5000000,
      direction: 'inflow',
      transaction_type: 'salary',
      currency: 'INR',
      reference_number: 'NEFT-SAL-001',
    },
    validation_status: 'valid',
    validation_errors: [],
    duplicate_status: 'none',
    confidence_score: 1.0,
    review_status: 'pending',
    selected_for_import: true,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
  {
    id: 'cand-2',
    import_batch_id: 'batch-456',
    workspace_id: 'ws-1',
    account_id: 'acct-hdfc',
    source_row_number: 2,
    raw_data: { Date: '14/11/2026', Narration: 'Amazon Retail', Withdrawal: '25000.00' },
    normalized_data: {
      transaction_date: '2026-11-14',
      description: 'Amazon Purchase Laptop',
      amount: '25000.0000',
      amount_paise: 2500000,
      direction: 'outflow',
      transaction_type: 'purchase',
      currency: 'INR',
      reference_number: 'AMZN-9988',
    },
    validation_status: 'valid',
    validation_errors: [],
    duplicate_status: 'exact',
    duplicate_reason: 'Exact match with existing transaction #tx-99',
    confidence_score: 1.0,
    review_status: 'pending',
    selected_for_import: false,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
  {
    id: 'cand-3',
    import_batch_id: 'batch-456',
    workspace_id: 'ws-1',
    account_id: 'acct-hdfc',
    source_row_number: 3,
    raw_data: { Date: '', Narration: 'Broken Row', Withdrawal: '0.00' },
    normalized_data: {
      transaction_date: null,
      description: 'Broken Row',
      amount: '0.0000',
      amount_paise: 0,
      direction: 'outflow',
      currency: 'INR',
    },
    validation_status: 'invalid',
    validation_errors: ['Missing or unparseable transaction date.', 'Transaction amount must be strictly greater than zero.'],
    duplicate_status: 'none',
    confidence_score: 1.0,
    review_status: 'pending',
    selected_for_import: false,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockJobs = [
  {
    id: 'job-1',
    workspace_id: 'ws-1',
    user_id: 'usr-1',
    source_type: 'csv',
    original_filename: 'sbi_october.csv',
    status: 'completed',
    total_records: 45,
    valid_records: 45,
    invalid_records: 0,
    duplicate_records: 2,
    imported_records: 43,
    created_at: '2026-11-10T10:00:00Z',
  },
];

describe('Import Page Component', () => {
  const fetchAccountsMock = vi.fn();
  const fetchJobsMock = vi.fn();
  const uploadFileMock = vi.fn();
  const confirmImportMock = vi.fn();
  const cancelJobMock = vi.fn();
  const toggleCandidateSelectionMock = vi.fn();
  const toggleSelectAllMock = vi.fn();
  const updateCandidateMock = vi.fn();
  const fetchReconciliationMock = vi.fn();
  const clearErrorMock = vi.fn();
  const resetCurrentUploadMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useAccountStore as any).mockReturnValue({
      accounts: mockAccounts,
      fetchAccounts: fetchAccountsMock,
    });
  });

  it('renders initial file upload dropzone and accounts selector', () => {
    (useImportStore as any).mockReturnValue({
      jobs: [],
      candidates: [],
      lastUploadResult: null,
      reconciliation: null,
      isLoading: false,
      isUploading: false,
      isConfirming: false,
      error: null,
      fetchJobs: fetchJobsMock,
      uploadFile: uploadFileMock,
      clearError: clearErrorMock,
      resetCurrentUpload: resetCurrentUploadMock,
    });

    render(<Import />);

    expect(screen.getByText('Financial Data Acquisition & Statement Import')).toBeInTheDocument();
    expect(screen.getByText('Upload Financial Statement')).toBeInTheDocument();
    expect(screen.getByText('HDFC Current Account (CURRENT - INR)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Inspect & Review Statement/i })).toBeInTheDocument();
  });

  it('renders candidate review table and metrics when upload result is present', () => {
    (useImportStore as any).mockReturnValue({
      jobs: mockJobs,
      candidates: mockCandidates,
      lastUploadResult: mockUploadResult,
      reconciliation: {
        batch_id: 'batch-456',
        opening_balance: '100000.0000',
        closing_balance: '125000.0000',
        total_inflows: '50000.0000',
        total_outflows: '25000.0000',
        calculated_closing_balance: '125000.0000',
        difference: '0.0000',
        is_reconciled: true,
        details: {},
      },
      isLoading: false,
      isUploading: false,
      isConfirming: false,
      error: null,
      fetchJobs: fetchJobsMock,
      confirmImport: confirmImportMock,
      cancelJob: cancelJobMock,
      toggleCandidateSelection: toggleCandidateSelectionMock,
      toggleSelectAll: toggleSelectAllMock,
      clearError: clearErrorMock,
    });

    render(<Import />);

    expect(screen.getByText('Salary Credit Corp Payroll')).toBeInTheDocument();
    expect(screen.getByText('Amazon Purchase Laptop')).toBeInTheDocument();
    expect(screen.getByText('Broken Row')).toBeInTheDocument();

    // Check metric counters
    expect(screen.getByText('Valid Ready to Post')).toBeInTheDocument();
    expect(screen.getByText('Suspected Duplicates')).toBeInTheDocument();
    expect(screen.getByText('Invalid / Ambiguous')).toBeInTheDocument();

    // Check reconciliation
    expect(screen.getByText('Statement Balance Reconciliation')).toBeInTheDocument();
    expect(screen.getByText(/Reconciled \(Zero Variance\)/i)).toBeInTheDocument();
  });

  it('filters candidates by status (valid, duplicates, invalid)', () => {
    (useImportStore as any).mockReturnValue({
      jobs: mockJobs,
      candidates: mockCandidates,
      lastUploadResult: mockUploadResult,
      reconciliation: null,
      isLoading: false,
      isUploading: false,
      isConfirming: false,
      error: null,
      fetchJobs: fetchJobsMock,
      toggleCandidateSelection: toggleCandidateSelectionMock,
      toggleSelectAll: toggleSelectAllMock,
    });

    render(<Import />);

    const dupsFilterBtn = screen.getByRole('button', { name: /Duplicates Only/i });
    fireEvent.click(dupsFilterBtn);

    expect(screen.getByText('Amazon Purchase Laptop')).toBeInTheDocument();
    expect(screen.queryByText('Salary Credit Corp Payroll')).not.toBeInTheDocument();
  });

  it('switches to import history tab and displays past statements', () => {
    (useImportStore as any).mockReturnValue({
      jobs: mockJobs,
      candidates: [],
      lastUploadResult: null,
      reconciliation: null,
      isLoading: false,
      isUploading: false,
      isConfirming: false,
      error: null,
      fetchJobs: fetchJobsMock,
    });

    render(<Import />);

    const historyTabBtn = screen.getByRole('button', { name: /Import History/i });
    fireEvent.click(historyTabBtn);

    expect(screen.getByText('Statement Import History')).toBeInTheDocument();
    expect(screen.getByText('sbi_october.csv')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });
});
