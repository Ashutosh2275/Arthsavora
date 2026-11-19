import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FinancialConnections } from '../FinancialConnections';
import { useFinancialConnectionStore } from '@/store/useFinancialConnectionStore';

// Mock zustand store
vi.mock('@/store/useFinancialConnectionStore');

const mockProviders = [
  {
    id: 'prov-1',
    provider_code: 'MOCK_SANDBOX_AA',
    name: 'Mock ReBIT AA Sandbox',
    category: 'account_aggregator',
    country: 'IN',
    auth_method: 'consent_token',
    is_sandbox: true,
    status: 'sandbox',
    supported_institutions: [
      { id: 'HDFC', name: 'HDFC Bank Ltd', code: 'HDFC0001' },
      { id: 'SBI', name: 'State Bank of India', code: 'SBIN0001' },
    ],
    capabilities: {
      account_discovery: true,
      transaction_sync: true,
      balance_refresh: true,
      historical_fetch_days: 365,
    },
    is_active: true,
  },
  {
    id: 'prov-2',
    provider_code: 'SETU_AA',
    name: 'Setu Account Aggregator',
    category: 'account_aggregator',
    country: 'IN',
    auth_method: 'consent_token',
    is_sandbox: false,
    status: 'unconfigured',
    supported_institutions: [{ id: 'ALL_BANKS', name: 'All Major Indian Banks', code: 'SETU_ALL' }],
    capabilities: {
      account_discovery: true,
      transaction_sync: true,
      balance_refresh: true,
      historical_fetch_days: 730,
    },
    is_active: true,
  },
];

const mockConnections = [
  {
    id: 'conn-1',
    workspace_id: 'ws-1',
    user_id: 'user-1',
    provider_id: 'prov-1',
    provider_code: 'MOCK_SANDBOX_AA',
    provider_name: 'Mock ReBIT AA Sandbox',
    institution_id: 'HDFC',
    institution_name: 'HDFC Bank Ltd',
    status: 'active',
    health_status: 'healthy',
    authorization_url: 'https://sandbox.rebit-aa.mock/auth/cons_mock_123',
    authorized_at: '2026-11-15T10:00:00Z',
    expires_at: '2027-05-14T10:00:00Z',
    last_attempted_sync_at: '2026-11-19T08:00:00Z',
    last_successful_sync_at: '2026-11-19T08:00:00Z',
    sync_failure_count: 0,
    sync_schedule: 'manual',
    created_at: '2026-11-15T10:00:00Z',
    active_consent: {
      id: 'cons-1',
      connection_id: 'conn-1',
      provider_consent_handle: 'cons_mock_123',
      status: 'active',
      purpose: 'Personal Financial Management & Automated Reconciliation',
      purpose_code: '101',
      data_categories: ['TRANSACTIONS', 'BALANCES', 'PROFILE'],
      account_types: ['savings', 'current'],
      valid_from: '2026-11-15T10:00:00Z',
      valid_to: '2027-05-14T10:00:00Z',
      created_at: '2026-11-15T10:00:00Z',
    },
    account_references: [
      {
        id: 'ref-1',
        connection_id: 'conn-1',
        provider_account_id: 'acc_hdfc_sb_001',
        fip_id: 'HDFC_FIP',
        institution_name: 'HDFC Bank Ltd',
        masked_account_number: '•••• 1234',
        account_type: 'savings',
        currency: 'INR',
        account_holder_name: 'Arthsavora Test User',
        current_balance_paise: 25400000,
        available_balance_paise: 25400000,
        status: 'linked',
        account_id: 'acc-internal-1',
        created_at: '2026-11-15T10:05:00Z',
      },
    ],
  },
];

const mockSyncHistory = [
  {
    id: 'job-1',
    connection_id: 'conn-1',
    workspace_id: 'ws-1',
    job_type: 'manual_sync',
    status: 'completed',
    records_retrieved: 3,
    records_imported: 3,
    duplicates_detected: 0,
    errors_encountered: 0,
    started_at: '2026-11-19T08:00:00Z',
    completed_at: '2026-11-19T08:00:05Z',
    created_at: '2026-11-19T08:00:00Z',
  },
];

const mockReconciliations = {
  'conn-1': [
    {
      id: 'rec-1',
      workspace_id: 'ws-1',
      account_id: 'acc-internal-1',
      connection_id: 'conn-1',
      reconciliation_date: '2026-11-19',
      provider_reported_balance_paise: 25400000,
      calculated_book_balance_paise: 25400000,
      difference_paise: 0,
      status: 'matched',
      explanation: 'Perfect balance reconciliation.',
      created_at: '2026-11-19T08:00:05Z',
    },
  ],
};

describe('FinancialConnections Page', () => {
  let mockStoreActions: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreActions = {
      providers: mockProviders,
      connections: mockConnections,
      selectedConnection: mockConnections[0],
      syncHistory: mockSyncHistory,
      reconciliations: mockReconciliations,
      isLoading: false,
      error: null,
      fetchProviders: vi.fn(),
      fetchConnections: vi.fn(),
      setSelectedConnection: vi.fn(),
      initiateConnection: vi.fn().mockResolvedValue(mockConnections[0]),
      authorizeConnection: vi.fn().mockResolvedValue(mockConnections[0]),
      triggerSync: vi.fn().mockResolvedValue(mockSyncHistory[0]),
      revokeConsent: vi.fn(),
      disconnectConnection: vi.fn().mockResolvedValue(true),
      linkAccount: vi.fn(),
      unlinkAccount: vi.fn(),
      fetchSyncHistory: vi.fn(),
      fetchReconciliations: vi.fn(),
      resolveReconciliation: vi.fn(),
    };

    (useFinancialConnectionStore as any).mockReturnValue(mockStoreActions);
  });

  it('renders page header and summary KPI metrics', () => {
    render(<FinancialConnections />);

    expect(screen.getByText('Financial Connections & Account Aggregation')).toBeInTheDocument();
    expect(screen.getByText('Connected Institutions')).toBeInTheDocument();
    expect(screen.getByText('Synchronized Accounts')).toBeInTheDocument();
    expect(screen.getByText('Consent Integrity')).toBeInTheDocument();
    expect(screen.getByText('Reconciliation Health')).toBeInTheDocument();
  });

  it('renders connected account cards in the Accounts tab', () => {
    render(<FinancialConnections />);

    expect(screen.getByText('HDFC Bank Ltd')).toBeInTheDocument();
    expect(screen.getByText('•••• 1234')).toBeInTheDocument();
    expect(screen.getByText('₹2,54,000.00')).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('displays empty state when no accounts or connections exist', () => {
    (useFinancialConnectionStore as any).mockReturnValue({
      ...mockStoreActions,
      connections: [],
      selectedConnection: null,
      reconciliations: {},
    });

    render(<FinancialConnections />);

    expect(screen.getByText('No Connected Financial Accounts')).toBeInTheDocument();
    expect(screen.getByText('Connect First Account')).toBeInTheDocument();
  });

  it('allows switching between tabs', async () => {
    render(<FinancialConnections />);

    // Switch to Providers & Banks tab
    const providersTab = screen.getByText(/Providers & Banks/i);
    fireEvent.click(providersTab);

    expect(screen.getByText('Mock ReBIT AA Sandbox')).toBeInTheDocument();
    expect(screen.getByText('Setu Account Aggregator')).toBeInTheDocument();

    // Switch to Balance Reconciliation tab
    const recTab = screen.getByText(/Balance Reconciliation/i);
    fireEvent.click(recTab);

    expect(screen.getByText(/Provider Reported vs Internal Book Balances/i)).toBeInTheDocument();
    expect(screen.getByText('MATCHED')).toBeInTheDocument();
  });

  it('opens Connect Institution modal when clicking Connect Institution button', () => {
    render(<FinancialConnections />);

    const connectBtn = screen.getByRole('button', { name: /Connect Institution/i });
    fireEvent.click(connectBtn);

    expect(screen.getByText('Connect Financial Institution via Account Aggregator')).toBeInTheDocument();
    expect(screen.getByText('Select Provider Gateway')).toBeInTheDocument();
    expect(screen.getByText('Select Target Banking Institution')).toBeInTheDocument();
  });

  it('triggers sync action when clicking Sync Now button on account card', async () => {
    render(<FinancialConnections />);

    const syncButton = screen.getByRole('button', { name: /Sync Now/i });
    fireEvent.click(syncButton);

    expect(mockStoreActions.triggerSync).toHaveBeenCalledWith('conn-1');
  });

  it('opens Disconnect confirmation dialog when clicking Disconnect button in details tab', () => {
    render(<FinancialConnections />);

    // Switch to details tab
    const detailsTab = screen.getByText(/Connection Details/i);
    fireEvent.click(detailsTab);

    const disconnectBtn = screen.getByRole('button', { name: /Disconnect/i });
    fireEvent.click(disconnectBtn);

    expect(screen.getByText('Disconnect Financial Connection')).toBeInTheDocument();
  });
});
