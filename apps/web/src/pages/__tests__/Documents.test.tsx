import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { TransactionMatchCandidate } from '@arthsavora/contracts';
import { Documents } from '../Documents';
import { useDocumentStore } from '@/store/useDocumentStore';
import { useAccountStore } from '@/store/useAccountStore';

vi.mock('@/store/useDocumentStore');
vi.mock('@/store/useAccountStore');

const mockAccounts = [
  {
    id: 'acc-1',
    name: 'HDFC Salary Account',
    account_type: 'bank',
    currency: 'INR',
    current_book_balance_paise: 25000000,
    available_balance_paise: 25000000,
  },
  {
    id: 'acc-2',
    name: 'ICICI Credit Card',
    account_type: 'credit_card',
    currency: 'INR',
    current_book_balance_paise: -150000,
    available_balance_paise: 35000000,
  },
];

const mockDocument = {
  id: 'doc-1',
  workspace_id: 'ws-1',
  uploaded_by_id: 'user-1',
  original_filename: 'swiggy_dinner_bill.pdf',
  file_size: 154200,
  mime_type: 'application/pdf',
  file_checksum: 'a1b2c3d4e5f6',
  document_type: 'receipt',
  status: 'review_required',
  preprocessing_metadata: {},
  retention_metadata: {},
  created_at: '2026-11-14T08:00:00Z',
  updated_at: '2026-11-14T08:00:05Z',
  extractions: [
    {
      id: 'ext-1',
      document_id: 'doc-1',
      workspace_id: 'ws-1',
      ocr_provider: 'pypdf_native',
      ocr_version: '1.0',
      raw_text: 'Swiggy Order #9812 Total: 567.50',
      structured_data: {
        merchant_name: 'Swiggy',
        gstin: '29AABCB2212M1Z2',
        receipt_date: '2026-11-12',
        invoice_number: 'SWG-9812',
        currency: 'INR',
        subtotal: '550.0000',
        subtotal_paise: 55000,
        taxes: {
          cgst: '13.7500',
          cgst_paise: 1375,
          sgst: '13.7500',
          sgst_paise: 1375,
          igst: '0.0000',
          igst_paise: 0,
          total_tax: '27.5000',
          total_tax_paise: 2750,
          gstin: '29AABCB2212M1Z2',
        },
        discount: '10.0000',
        discount_paise: 1000,
        total_amount: '567.5000',
        total_amount_paise: 56750,
        payment_method: 'upi',
        payment_reference: '628491028472',
        line_items: [
          {
            description: 'Paneer Butter Masala',
            quantity: '1.0',
            unit_price: '280.00',
            unit_price_paise: 28000,
            amount: '280.00',
            amount_paise: 28000,
          },
          {
            description: 'Butter Naan',
            quantity: '2.0',
            unit_price: '60.00',
            unit_price_paise: 6000,
            amount: '120.00',
            amount_paise: 12000,
          },
        ],
      },
      field_confidences: {
        merchant_name: 0.95,
        total_amount: 0.98,
        gstin: 0.99,
      },
      overall_confidence: '0.9400',
      validation_status: 'warning',
      validation_warnings: ['Minor rounding discrepancy of 50 paise observed.'],
      created_at: '2026-11-14T08:00:05Z',
    },
  ],
  reviews: [],
  transaction_associations: [],
};

const mockMatches: TransactionMatchCandidate[] = [
  {
    transaction_id: 'tx-1234',
    match_status: 'exact',
    match_score: '0.9500',
    evidence: { amount_match: 'exact', date_match: 'same_day' },
    transaction_summary: {
      id: 'tx-1234',
      transaction_date: '2026-11-12',
      amount: '567.50',
      amount_paise: 56750,
      description: 'Swiggy Bangalore Order',
      direction: 'outflow',
    },
  },
];

describe('Documents Page Component', () => {
  let fetchDocumentsMock: any;
  let fetchDocumentDetailsMock: any;
  let uploadDocumentMock: any;
  let processDocumentMock: any;
  let correctExtractionMock: any;
  let confirmTransactionMock: any;
  let findMatchesMock: any;
  let associateTransactionMock: any;
  let rejectDocumentMock: any;
  let deleteDocumentMock: any;
  let setSelectedDocumentMock: any;
  let clearErrorMock: any;
  let fetchAccountsMock: any;

  beforeEach(() => {
    vi.clearAllMocks();

    fetchDocumentsMock = vi.fn();
    fetchDocumentDetailsMock = vi.fn();
    uploadDocumentMock = vi.fn();
    processDocumentMock = vi.fn();
    correctExtractionMock = vi.fn();
    confirmTransactionMock = vi.fn();
    findMatchesMock = vi.fn().mockResolvedValue(mockMatches);
    associateTransactionMock = vi.fn();
    rejectDocumentMock = vi.fn();
    deleteDocumentMock = vi.fn();
    setSelectedDocumentMock = vi.fn();
    clearErrorMock = vi.fn();
    fetchAccountsMock = vi.fn();

    (useAccountStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      accounts: mockAccounts,
      fetchAccounts: fetchAccountsMock,
    });

    (useDocumentStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      documents: [mockDocument],
      totalDocuments: 1,
      selectedDocument: mockDocument,
      matches: mockMatches,
      isLoading: false,
      isUploading: false,
      isProcessing: false,
      isMatching: false,
      error: null,
      fetchDocuments: fetchDocumentsMock,
      fetchDocumentDetails: fetchDocumentDetailsMock,
      uploadDocument: uploadDocumentMock,
      processDocument: processDocumentMock,
      correctExtraction: correctExtractionMock,
      confirmTransaction: confirmTransactionMock,
      findMatches: findMatchesMock,
      associateTransaction: associateTransactionMock,
      rejectDocument: rejectDocumentMock,
      deleteDocument: deleteDocumentMock,
      setSelectedDocument: setSelectedDocumentMock,
      clearError: clearErrorMock,
    });
  });

  it('renders the header and document intelligence overview', () => {
    render(<Documents />);

    expect(screen.getByText('Receipt Intelligence & Documents')).toBeDefined();
    expect(screen.getByText(/India-first receipt OCR, GSTIN validation/i)).toBeDefined();
    expect(screen.getByText('Upload Document')).toBeDefined();
    expect(screen.getByText(/Drop physical receipt scans/i)).toBeDefined();
  });

  it('renders document list items with status and parsed totals', () => {
    render(<Documents />);

    expect(screen.getByText('Swiggy')).toBeDefined();
    expect(screen.getByText('₹567.5000')).toBeDefined();
    expect(screen.getAllByText(/review required/i).length).toBeGreaterThanOrEqual(1);
  });

  it('displays extracted entities including merchant, total, GSTIN, and line items', () => {
    render(<Documents />);

    // Merchant and invoice
    expect(screen.getByDisplayValue('Swiggy')).toBeDefined();
    expect(screen.getByDisplayValue('567.5000')).toBeDefined();
    expect(screen.getByDisplayValue('29AABCB2212M1Z2')).toBeDefined();

    // Line items
    expect(screen.getByText('Paneer Butter Masala')).toBeDefined();
    expect(screen.getByText('Butter Naan')).toBeDefined();

    // Confidence badge
    expect(screen.getByText('94% Confidence')).toBeDefined();
  });

  it('triggers field corrections update when Save Field Corrections is clicked', async () => {
    render(<Documents />);

    const saveBtn = screen.getByText('Save Field Corrections');
    fireEvent.click(saveBtn);

    expect(correctExtractionMock).toHaveBeenCalledWith(
      'doc-1',
      expect.objectContaining({
        merchant_name: 'Swiggy',
        total_amount: '567.5000',
        gstin: '29AABCB2212M1Z2',
      })
    );
  });

  it('displays transaction match candidates with linking action', () => {
    render(<Documents />);

    expect(screen.getByText(/Matching Existing Transactions/i)).toBeDefined();
    expect(screen.getByText('Swiggy Bangalore Order')).toBeDefined();
    expect(screen.getByText(/EXACT/i)).toBeDefined();

    const linkBtn = screen.getByText('Link Receipt');
    fireEvent.click(linkBtn);

    expect(associateTransactionMock).toHaveBeenCalledWith(
      'doc-1',
      'tx-1234',
      0.95,
      'Linked via match candidate scan'
    );
  });

  it('executes explicit user confirmation and posts authoritative transaction', async () => {
    render(<Documents />);

    const confirmBtn = screen.getByText('Confirm & Post Transaction');
    fireEvent.click(confirmBtn);

    expect(confirmTransactionMock).toHaveBeenCalledWith(
      'doc-1',
      'acc-1',
      expect.objectContaining({
        merchant_name: 'Swiggy',
        total_amount: '567.5000',
      })
    );
  });
});
