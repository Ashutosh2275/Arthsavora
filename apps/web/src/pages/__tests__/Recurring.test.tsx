import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Recurring from '../Recurring';
import { useRecurringStore } from '@/store/useRecurringStore';
import { useSubscriptionStore } from '@/store/useSubscriptionStore';

vi.mock('@/store/useRecurringStore');
vi.mock('@/store/useSubscriptionStore');

const mockCommitments = {
  workspace_id: 'ws-1',
  window_days: 30,
  start_date: '2026-11-14',
  end_date: '2026-12-14',
  total_expected_inflow_paise: 12000000,
  total_expected_inflow: 120000,
  total_expected_outflow_paise: 4500000,
  total_expected_outflow: 45000,
  net_commitment_paise: 7500000,
  net_commitment: 75000,
  active_recurring_count: 3,
  active_subscription_count: 2,
  normalized_monthly_expenses_paise: 4500000,
  normalized_monthly_expenses: 45000,
  normalized_annual_expenses_paise: 54000000,
  normalized_annual_expenses: 540000,
  commitments_by_category: [
    { category_name: 'Housing & Rent', count: 1, total_amount_paise: 2500000, total_amount: 25000 },
  ],
  commitments_by_type: [
    { type_name: 'Rent & Housing', count: 1, total_amount_paise: 2500000, total_amount: 25000 },
    { type_name: 'Subscriptions', count: 1, total_amount_paise: 64900, total_amount: 649 },
  ],
  upcoming_occurrences: [
    {
      id: 'occ-1',
      workspace_id: 'ws-1',
      recurring_definition_id: 'def-1',
      recurring_name: 'Apartment Rent',
      direction: 'outflow',
      expected_date: '2026-12-01',
      expected_amount_paise: 2500000,
      expected_amount: 25000,
      currency: 'INR',
      status: 'scheduled',
      matched_transaction_id: null,
      matched_amount_paise: null,
      matched_amount: null,
      amount_variance_paise: null,
      match_confidence: null,
      notes: null,
      generated_at: '2026-11-14T00:00:00Z',
      confirmed_at: null,
      updated_at: '2026-11-14T00:00:00Z',
    },
  ],
};

const mockDefinitions = [
  {
    id: 'def-1',
    workspace_id: 'ws-1',
    name: 'Apartment Rent',
    description: 'Monthly flat rent',
    direction: 'outflow',
    transaction_type: 'expense',
    expected_amount_paise: 2500000,
    expected_amount: 25000,
    is_variable_amount: false,
    currency: 'INR',
    category_id: null,
    category_name: 'Housing & Rent',
    merchant_id: null,
    merchant_name: 'Landlord',
    account_id: null,
    account_name: 'HDFC Salary',
    frequency: 'monthly',
    interval: 1,
    day_of_month: 1,
    day_of_week: null,
    end_of_month_policy: 'last_day',
    start_date: '2026-01-01',
    end_date: null,
    next_expected_date: '2026-12-01',
    timezone: 'Asia/Kolkata',
    status: 'active',
    normalized_monthly_paise: 2500000,
    normalized_annual_paise: 30000000,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockSubscriptions = [
  {
    id: 'sub-1',
    workspace_id: 'ws-1',
    recurring_definition_id: null,
    name: 'Netflix Premium',
    provider_name: 'Netflix',
    merchant_id: null,
    merchant_name: null,
    category_id: null,
    category_name: 'Entertainment',
    expected_amount_paise: 64900,
    expected_amount: 649,
    currency: 'INR',
    billing_frequency: 'monthly',
    billing_cycle_interval: 1,
    start_date: '2026-01-01',
    next_billing_date: '2026-12-05',
    renewal_date: null,
    trial_end_date: null,
    cancellation_date: null,
    account_id: null,
    account_name: null,
    payment_method_display: 'HDFC Credit Card ending 4092',
    status: 'active',
    is_variable_pricing: false,
    notes: null,
    estimated_monthly_paise: 64900,
    estimated_annual_paise: 778800,
    created_at: '2026-11-14T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
];

const mockSuggestions = [
  {
    id: 'sugg-1',
    workspace_id: 'ws-1',
    merchant_id: null,
    merchant_name: 'Spotify India',
    normalized_description: 'SPOTIFY INDIA MUMBAI',
    direction: 'outflow',
    suggested_frequency: 'monthly',
    suggested_amount_paise: 11900,
    suggested_amount: 119,
    min_amount_paise: 11900,
    max_amount_paise: 11900,
    currency: 'INR',
    category_id: null,
    confidence_score: 0.92,
    evidence_count: 4,
    evidence_summary: { count: 4 },
    first_seen_date: '2026-07-05',
    last_seen_date: '2026-10-05',
    estimated_next_date: '2026-11-05',
    status: 'pending',
    dismissed_reason: null,
    created_at: '2026-11-14T00:00:00Z',
  },
];

describe('Recurring & Subscriptions Page', () => {
  const mockFetchDefinitions = vi.fn();
  const mockFetchCommitments = vi.fn();
  const mockFetchSuggestions = vi.fn();
  const mockRunDetection = vi.fn();
  const mockCreateDefinition = vi.fn();
  const mockPauseDefinition = vi.fn();
  const mockResumeDefinition = vi.fn();
  const mockCancelDefinition = vi.fn();
  const mockSkipOccurrence = vi.fn();
  const mockConfirmOccurrence = vi.fn();
  const mockMatchOccurrence = vi.fn();
  const mockConfirmSuggestion = vi.fn();
  const mockDismissSuggestion = vi.fn();

  const mockFetchSubscriptions = vi.fn();
  const mockCreateSubscription = vi.fn();
  const mockCancelSubscription = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useRecurringStore as unknown as any).mockReturnValue({
      definitions: mockDefinitions,
      commitments: mockCommitments,
      occurrences: [],
      suggestions: mockSuggestions,
      loading: false,
      commitmentsLoading: false,
      detecting: false,
      error: null,
      fetchDefinitions: mockFetchDefinitions,
      fetchCommitments: mockFetchCommitments,
      fetchSuggestions: mockFetchSuggestions,
      runDetection: mockRunDetection,
      createDefinition: mockCreateDefinition,
      pauseDefinition: mockPauseDefinition,
      resumeDefinition: mockResumeDefinition,
      cancelDefinition: mockCancelDefinition,
      skipOccurrence: mockSkipOccurrence,
      confirmOccurrence: mockConfirmOccurrence,
      matchOccurrence: mockMatchOccurrence,
      confirmSuggestion: mockConfirmSuggestion,
      dismissSuggestion: mockDismissSuggestion,
    });

    (useSubscriptionStore as unknown as any).mockReturnValue({
      subscriptions: mockSubscriptions,
      loading: false,
      error: null,
      fetchSubscriptions: mockFetchSubscriptions,
      createSubscription: mockCreateSubscription,
      cancelSubscription: mockCancelSubscription,
    });
  });

  it('renders recurring page header and upcoming commitments KPI cards', () => {
    render(<Recurring />);

    expect(screen.getByText('Recurring & Commitments')).toBeInTheDocument();
    expect(screen.getByText('Upcoming Commitments')).toBeInTheDocument();
    expect(screen.getByText('Expected Outflow')).toBeInTheDocument();
    expect(screen.getByText('Expected Inflow')).toBeInTheDocument();
    expect(screen.getByText('Net Forward Commitment')).toBeInTheDocument();
    expect(screen.getByText('Apartment Rent')).toBeInTheDocument();
  });

  it('switches between tabs cleanly', () => {
    render(<Recurring />);

    // Switch to Recurring Schedules tab
    const schedulesTab = screen.getByRole('button', { name: /Recurring Schedules/i });
    fireEvent.click(schedulesTab);
    expect(screen.getByText('Active Recurring Schedules')).toBeInTheDocument();

    // Switch to Subscriptions tab
    const subsTab = screen.getByRole('button', { name: /Subscriptions/i });
    fireEvent.click(subsTab);
    expect(screen.getByText('Netflix Premium')).toBeInTheDocument();

    // Switch to Pattern Suggestions tab
    const suggTab = screen.getByRole('button', { name: /Pattern Suggestions/i });
    fireEvent.click(suggTab);
    expect(screen.getByText('Spotify India')).toBeInTheDocument();
    expect(screen.getByText('92% Confidence')).toBeInTheDocument();
  });

  it('triggers pattern detection scan when detect button is clicked', () => {
    render(<Recurring />);

    const scanBtn = screen.getByRole('button', { name: /Detect Recurring/i });
    fireEvent.click(scanBtn);

    expect(mockRunDetection).toHaveBeenCalledWith(180);
  });

  it('opens add recurring definition modal', () => {
    render(<Recurring />);

    const addBtn = screen.getByRole('button', { name: /\+ Recurring Activity/i });
    fireEvent.click(addBtn);

    expect(screen.getByText('Create Recurring Financial Activity')).toBeInTheDocument();
    expect(screen.getByLabelText(/Name \/ Title/i)).toBeInTheDocument();
  });

  it('handles empty state when no upcoming commitments exist', () => {
    (useRecurringStore as unknown as any).mockReturnValue({
      definitions: [],
      commitments: { ...mockCommitments, upcoming_occurrences: [] },
      occurrences: [],
      suggestions: [],
      loading: false,
      commitmentsLoading: false,
      detecting: false,
      error: null,
      fetchDefinitions: mockFetchDefinitions,
      fetchCommitments: mockFetchCommitments,
      fetchSuggestions: mockFetchSuggestions,
      runDetection: mockRunDetection,
      createDefinition: mockCreateDefinition,
      pauseDefinition: mockPauseDefinition,
      resumeDefinition: mockResumeDefinition,
      cancelDefinition: mockCancelDefinition,
      skipOccurrence: mockSkipOccurrence,
      confirmOccurrence: mockConfirmOccurrence,
      matchOccurrence: mockMatchOccurrence,
      confirmSuggestion: mockConfirmSuggestion,
      dismissSuggestion: mockDismissSuggestion,
    });

    render(<Recurring />);
    expect(screen.getByText('No upcoming commitments')).toBeInTheDocument();
  });
});
