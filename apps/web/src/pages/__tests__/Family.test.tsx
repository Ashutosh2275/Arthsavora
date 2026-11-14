import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Family } from '../Family';
import { useFamilyStore } from '@/store/useFamilyStore';

vi.mock('@/store/useFamilyStore');

const mockOverview = {
  profile: {
    id: 'prof-1',
    workspace_id: 'ws-fam-1',
    household_name: 'Sharma Household',
    household_currency: 'INR',
    household_timezone: 'Asia/Kolkata',
    monthly_budget_start_day: 1,
    default_allocation_method: 'equal',
    contribution_reminder_day: 25,
    enable_shared_budget_alerts: true,
    enable_contribution_reminders: true,
    settings: {},
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-14T00:00:00Z',
  },
  member_count: 3,
  total_household_income_paise: 25000000,
  total_household_income_decimal: 250000.0,
  total_household_expense_paise: 9500000,
  total_household_expense_decimal: 95000.0,
  net_household_savings_paise: 15500000,
  net_household_savings_decimal: 155000.0,
  shared_account_balances_paise: 42000000,
  shared_account_balances_decimal: 420000.0,
  budget_utilization_pct: 75.5,
  active_budgets_count: 4,
  active_goals_count: 2,
  upcoming_commitments_count: 3,
  top_expense_categories: [
    { category: 'Groceries', amount_paise: 3500000, amount_decimal: 35000.0 },
    { category: 'Utilities', amount_paise: 1500000, amount_decimal: 15000.0 },
  ],
  recent_shared_transactions: [
    {
      id: 'tx-1',
      description: 'Nature Basket Supermarket',
      amount_paise: 425000,
      amount_decimal: 4250.0,
      currency: 'INR',
      direction: 'outflow',
      transaction_date: '2026-11-14',
      paid_by: 'Rohit Sharma',
    },
  ],
};

const mockMembers = [
  {
    id: 'mem-1',
    workspace_id: 'ws-fam-1',
    user_id: 'user-1',
    email: 'rohit@example.com',
    full_name: 'Rohit Sharma',
    role: 'owner',
    status: 'active',
    joined_at: '2026-11-01T00:00:00Z',
  },
  {
    id: 'mem-2',
    workspace_id: 'ws-fam-1',
    user_id: 'user-2',
    email: 'ananya@example.com',
    full_name: 'Ananya Sharma',
    role: 'admin',
    status: 'active',
    joined_at: '2026-11-02T00:00:00Z',
  },
];

const mockAllocations = [
  {
    id: 'alloc-1',
    workspace_id: 'ws-fam-1',
    transaction_id: 'tx-1',
    transaction_description: 'Grocery Provisions',
    allocation_method: 'equal',
    total_amount_paise: 400000,
    total_amount_decimal: 4000.0,
    currency: 'INR',
    status: 'active',
    version: 1,
    notes: 'Weekly staples',
    items: [
      {
        id: 'it-1',
        member_user_id: 'user-1',
        member_name: 'Rohit Sharma',
        assigned_share_paise: 200000,
        assigned_share_decimal: 2000.0,
        percentage: 50.0,
        is_paid_by: true,
        settlement_status: 'settled',
      },
      {
        id: 'it-2',
        member_user_id: 'user-2',
        member_name: 'Ananya Sharma',
        assigned_share_paise: 200000,
        assigned_share_decimal: 2000.0,
        percentage: 50.0,
        is_paid_by: false,
        settlement_status: 'pending',
      },
    ],
    created_at: '2026-11-14T08:00:00Z',
  },
];

const mockSettlement = {
  workspace_id: 'ws-fam-1',
  period: '2026-11',
  currency: 'INR',
  total_shared_expenses_paise: 400000,
  total_shared_expenses_decimal: 4000.0,
  total_contributions_paid_paise: 5000000,
  total_contributions_paid_decimal: 50000.0,
  total_allocated_paise: 400000,
  total_allocated_decimal: 4000.0,
  member_settlements: [
    {
      member_user_id: 'user-1',
      full_name: 'Rohit Sharma',
      email: 'rohit@example.com',
      role: 'owner',
      total_expenses_paid_paise: 400000,
      total_expenses_paid_decimal: 4000.0,
      total_contributions_paid_paise: 2500000,
      total_contributions_paid_decimal: 25000.0,
      total_allocated_share_paise: 200000,
      total_allocated_share_decimal: 2000.0,
      net_position_paise: 2700000,
      net_position_decimal: 27000.0,
      currency: 'INR',
      status: 'surplus',
    },
    {
      member_user_id: 'user-2',
      full_name: 'Ananya Sharma',
      email: 'ananya@example.com',
      role: 'admin',
      total_expenses_paid_paise: 0,
      total_expenses_paid_decimal: 0.0,
      total_contributions_paid_paise: 2500000,
      total_contributions_paid_decimal: 25000.0,
      total_allocated_share_paise: 200000,
      total_allocated_share_decimal: 2000.0,
      net_position_paise: 2300000,
      net_position_decimal: 23000.0,
      currency: 'INR',
      status: 'surplus',
    },
  ],
  recommendations: [],
};

describe('Family Finance Page Component', () => {
  const fetchOverviewMock = vi.fn();
  const fetchMembersMock = vi.fn();
  const fetchAllocationsMock = vi.fn();
  const fetchContributionsMock = vi.fn();
  const fetchSettlementsMock = vi.fn();
  const fetchSharedAccountsMock = vi.fn();
  const fetchActivitiesMock = vi.fn();
  const inviteMemberMock = vi.fn().mockResolvedValue({ id: 'inv-1' });
  const createAllocationMock = vi.fn().mockResolvedValue({ id: 'alloc-1' });

  beforeEach(() => {
    vi.clearAllMocks();
    (useFamilyStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      overview: mockOverview,
      profile: mockOverview.profile,
      members: mockMembers,
      allocations: mockAllocations,
      contributions: [],
      settlement: mockSettlement,
      sharedAccounts: [],
      activities: [],
      isLoading: false,
      error: null,
      fetchOverview: fetchOverviewMock,
      fetchMembers: fetchMembersMock,
      fetchAllocations: fetchAllocationsMock,
      fetchContributions: fetchContributionsMock,
      fetchSettlements: fetchSettlementsMock,
      fetchSharedAccounts: fetchSharedAccountsMock,
      fetchActivities: fetchActivitiesMock,
      inviteMember: inviteMemberMock,
      updateMemberRole: vi.fn(),
      removeMember: vi.fn(),
      createAllocation: createAllocationMock,
      recordContribution: vi.fn(),
      updateContribution: vi.fn(),
      shareAccount: vi.fn(),
      revokeSharedAccount: vi.fn(),
    });
  });

  it('renders the household header and KPI summary cards correctly', () => {
    render(<Family />);

    expect(screen.getByText('Sharma Household')).toBeInTheDocument();
    expect(screen.getByText('Household Workspace')).toBeInTheDocument();
    expect(screen.getByText('Household Income')).toBeInTheDocument();
    expect(screen.getByText('Household Expenses')).toBeInTheDocument();
    expect(screen.getByText('Net Savings')).toBeInTheDocument();
    expect(screen.getByText('Shared Balances')).toBeInTheDocument();
    expect(screen.getByText('75.5%')).toBeInTheDocument();
  });

  it('switches to Members tab and displays member directory', () => {
    render(<Family />);

    const membersTab = screen.getByText(/Members & Privacy/);
    fireEvent.click(membersTab);

    expect(screen.getByText('Household Members')).toBeInTheDocument();
    expect(screen.getByText('Rohit Sharma')).toBeInTheDocument();
    expect(screen.getByText('Ananya Sharma')).toBeInTheDocument();
    expect(screen.getByText('owner')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('switches to Expense Allocations tab and displays allocation cards', () => {
    render(<Family />);

    const allocTab = screen.getByText(/Expense Allocations/);
    fireEvent.click(allocTab);

    expect(screen.getByText('Grocery Provisions')).toBeInTheDocument();
    expect(screen.getByText(/equal/i)).toBeInTheDocument();
    expect(screen.getAllByText(/₹2,000/).length).toBeGreaterThan(0);
  });

  it('switches to Settlements tab and renders member standings', () => {
    render(<Family />);

    const settlementsTab = screen.getByText(/Settlements & Net Standing/);
    fireEvent.click(settlementsTab);

    expect(screen.getByText('Member Net Standing')).toBeInTheDocument();
    expect(screen.getByText('Suggested Informational Settlements')).toBeInTheDocument();
    expect(screen.getAllByText('surplus').length).toBeGreaterThan(0);
  });

  it('opens Invite Member modal and triggers invitation', async () => {
    render(<Family />);

    const inviteBtn = screen.getByRole('button', { name: /Invite Member/i });
    fireEvent.click(inviteBtn);

    expect(screen.getByText('Email Address')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('family.member@example.com');
    fireEvent.change(input, { target: { value: 'rahul@example.com' } });

    const sendBtn = screen.getByRole('button', { name: /Send Invitation/i });
    fireEvent.click(sendBtn);

    expect(inviteMemberMock).toHaveBeenCalledWith('rahul@example.com', 'member');
  });

  it('opens New Allocation modal and triggers allocation creation', async () => {
    render(<Family />);

    const allocBtn = screen.getByRole('button', { name: /New Allocation/i });
    fireEvent.click(allocBtn);

    expect(screen.getByText('Transaction ID (UUID)')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6');
    fireEvent.change(input, { target: { value: '11111111-2222-3333-4444-555555555555' } });

    const submitBtn = screen.getByRole('button', { name: /Create Allocation/i });
    fireEvent.click(submitBtn);

    expect(createAllocationMock).toHaveBeenCalledWith({
      transaction_id: '11111111-2222-3333-4444-555555555555',
      allocation_method: 'equal',
      notes: undefined,
    });
  });
});
