import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Anomalies } from '../Anomalies';
import { useAnomalyStore } from '@/store/useAnomalyStore';

vi.mock('@/store/useAnomalyStore');

const mockAnomaly = {
  id: 'anom-1',
  workspace_id: 'ws-1',
  transaction_id: 'tx-1',
  account_id: 'acc-1',
  detection_type: 'amount',
  detection_method: 'deterministic_rule',
  severity: 'high',
  risk_score: 82,
  status: 'new',
  explanation: 'Transaction amount of ₹65,000.00 exceeds your high-value threshold of ₹50,000.00.',
  evidence_metadata: {
    amount_paise: 6500000,
    threshold_paise: 5000000,
    ratio: 1.3,
  },
  rule_code: 'RULE_HIGH_AMOUNT',
  model_version: 'v1.0.0',
  detected_at: '2026-11-14T08:00:00Z',
  resolved_at: null,
  resolved_by_id: null,
  resolution_notes: null,
  transaction: {
    id: 'tx-1',
    transaction_date: '2026-11-14',
    amount_paise: 6500000,
    amount: 65000,
    currency: 'INR',
    direction: 'outflow',
    description: 'Luxury Electronic Store',
    merchant_name: 'Apple Store',
    category_name: 'Electronics',
    account_name: 'Main Checking',
  },
  reviews: [],
};

const mockSummary = {
  total_detections: 8,
  open_anomalies: 3,
  high_severity_anomalies: 2,
  resolved_anomalies: 5,
  average_risk_score: 64.5,
};

const mockRules = [
  {
    id: 'rule-1',
    workspace_id: null,
    rule_code: 'RULE_HIGH_AMOUNT',
    name: 'Unusually High Transaction Amount',
    description: 'Flags single transactions exceeding threshold.',
    detection_category: 'amount',
    severity: 'high',
    threshold_config: { threshold_paise: 5000000 },
    is_enabled: true,
    version: '1.0.0',
  },
  {
    id: 'rule-2',
    workspace_id: null,
    rule_code: 'RULE_FREQUENCY_BURST',
    name: 'Rapid Multi-Transaction Burst',
    description: 'Flags multiple transactions in short interval.',
    detection_category: 'frequency',
    severity: 'high',
    threshold_config: { window_minutes: 30, count_threshold: 3 },
    is_enabled: true,
    version: '1.0.0',
  },
];

const mockExceptions = [
  {
    id: 'exc-1',
    workspace_id: 'ws-1',
    rule_code: 'RULE_HIGH_AMOUNT',
    merchant_id: null,
    merchant_name: 'University Tuition',
    category_id: null,
    category_name: null,
    account_id: null,
    account_name: null,
    merchant_name_pattern: 'Tuition',
    max_amount_paise: 15000000,
    max_amount: 150000,
    reason: 'Verified university semester fee',
    expires_at: '2027-11-14',
    created_at: '2026-11-14T00:00:00Z',
  },
];

describe('Financial Security & Anomaly Intelligence Page', () => {
  const fetchAnomaliesMock = vi.fn();
  const fetchSummaryMock = vi.fn();
  const fetchRulesMock = vi.fn();
  const fetchExceptionsMock = vi.fn();
  const scanRecentTransactionsMock = vi.fn();
  const reviewAnomalyMock = vi.fn();
  const acknowledgeAnomalyMock = vi.fn();
  const dismissAnomalyMock = vi.fn();
  const updateRuleMock = vi.fn();
  const createExceptionMock = vi.fn();
  const deleteExceptionMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAnomalyStore as any).mockReturnValue({
      anomalies: [mockAnomaly],
      summary: mockSummary,
      rules: mockRules,
      exceptions: mockExceptions,
      statusFilter: null,
      severityFilter: null,
      isLoading: false,
      error: null,
      setStatusFilter: vi.fn(),
      setSeverityFilter: vi.fn(),
      fetchAnomalies: fetchAnomaliesMock,
      fetchSummary: fetchSummaryMock,
      fetchRules: fetchRulesMock,
      fetchExceptions: fetchExceptionsMock,
      scanRecentTransactions: scanRecentTransactionsMock,
      reviewAnomaly: reviewAnomalyMock,
      acknowledgeAnomaly: acknowledgeAnomalyMock,
      dismissAnomaly: dismissAnomalyMock,
      updateRule: updateRuleMock,
      createException: createExceptionMock,
      deleteException: deleteExceptionMock,
    });
  });

  it('renders page header, risk intelligence title, and KPI cards correctly', () => {
    render(<Anomalies />);

    expect(screen.getByText('Financial Security & Risk Intelligence')).toBeInTheDocument();
    expect(screen.getByText('Open Anomalies')).toBeInTheDocument();
    expect(screen.getByText('High / Critical Risk')).toBeInTheDocument();
    expect(screen.getByText('Average Risk Score')).toBeInTheDocument();
    expect(screen.getByText('Resolved / Dismissed')).toBeInTheDocument();

    // Check summary numbers
    expect(screen.getByText('3')).toBeInTheDocument(); // open anomalies
    expect(screen.getByText('2')).toBeInTheDocument(); // high severity
    expect(screen.getByText('64.5')).toBeInTheDocument(); // average risk score
  });

  it('renders anomaly card with explanation, risk score, and transaction details', () => {
    render(<Anomalies />);

    expect(screen.getByText(/exceeds your high-value threshold of ₹50,000.00/i)).toBeInTheDocument();
    expect(screen.getByText('Score: 82/100')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('Apple Store')).toBeInTheDocument();
    expect(screen.getByText('deterministic_rule')).toBeInTheDocument();
  });

  it('switches between tabs cleanly (Feed, Rules, Exceptions)', () => {
    render(<Anomalies />);

    // Switch to Detection Rules
    const rulesTab = screen.getByText(/Detection Rules/i);
    fireEvent.click(rulesTab);

    expect(screen.getByText('Deterministic Anomaly Detection Rules')).toBeInTheDocument();
    expect(screen.getByText('Unusually High Transaction Amount')).toBeInTheDocument();
    expect(screen.getByText('Rapid Multi-Transaction Burst')).toBeInTheDocument();

    // Switch to Whitelist Exceptions
    const exceptionsTab = screen.getByText(/Whitelist Exceptions/i);
    fireEvent.click(exceptionsTab);

    expect(screen.getByText('Detection Whitelist Exceptions')).toBeInTheDocument();
    expect(screen.getByText('University Tuition')).toBeInTheDocument();
    expect(screen.getByText(/Verified university semester fee/i)).toBeInTheDocument();
  });

  it('opens review modal when clicking Review on an anomaly', () => {
    render(<Anomalies />);

    const reviewButton = screen.getByRole('button', { name: /^Review$/i });
    fireEvent.click(reviewButton);

    expect(screen.getByText('Review Financial Anomaly')).toBeInTheDocument();
    expect(screen.getByText('Reason for Detection:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Confirm Review/i })).toBeInTheDocument();
  });

  it('triggers quick actions (Acknowledge and Dismiss)', () => {
    render(<Anomalies />);

    const ackBtn = screen.getByRole('button', { name: /^Acknowledge$/i });
    fireEvent.click(ackBtn);
    expect(acknowledgeAnomalyMock).toHaveBeenCalledWith('anom-1');

    const dismissBtn = screen.getByRole('button', { name: /^Dismiss$/i });
    fireEvent.click(dismissBtn);
    expect(dismissAnomalyMock).toHaveBeenCalledWith('anom-1', 'Dismissed from feed');
  });
});
