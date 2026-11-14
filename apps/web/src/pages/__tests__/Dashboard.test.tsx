import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from '../Dashboard';
import { useAnalyticsStore } from '@/store/useAnalyticsStore';
import { useAccountStore } from '@/store/useAccountStore';

vi.mock('@/store/useAnalyticsStore');
vi.mock('@/store/useAccountStore');

// Mock recharts ResponsiveContainer to avoid SVG measurement errors in JSDOM
vi.mock('recharts', async () => {
  const actual: any = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div className="recharts-responsive-container">{children}</div>,
  };
});

const mockOverview = {
  workspace_id: 'ws-1',
  currency: 'INR',
  start_date: '2026-02-01',
  end_date: '2026-02-28',
  total_income_paise: 15000000,
  total_income: 150000.0,
  gross_expenses_paise: 8500000,
  refunds_paise: 500000,
  total_expenses_paise: 8000000,
  total_expenses: 80000.0,
  net_cash_flow_paise: 7000000,
  net_cash_flow: 70000.0,
  savings_paise: 7000000,
  savings: 70000.0,
  savings_rate_percentage: 46.67,
  transaction_count: 42,
  average_daily_spend_paise: 285714,
  average_daily_spend: 2857.14,
  days_in_period: 28,
  data_quality: {
    uncategorized_count: 3,
    uncategorized_amount_paise: 450000,
    uncategorized_amount: 4500.0,
    excluded_transfers_count: 4,
    excluded_transfers_amount_paise: 5000000,
    excluded_transfers_amount: 50000.0,
    excluded_pending_count: 2,
    excluded_pending_amount_paise: 120000,
    excluded_pending_amount: 1200.0,
  },
};

const mockNetWorth = {
  workspace_id: 'ws-1',
  currency: 'INR',
  as_of_date: '2026-02-14',
  total_assets_paise: 52000000,
  total_assets: 520000.0,
  total_liabilities_paise: 4500000,
  total_liabilities: 45000.0,
  net_worth_paise: 47500000,
  net_worth: 475000.0,
  asset_accounts: [
    {
      id: 'acc-1',
      name: 'HDFC Salary Bank',
      account_type: 'salary',
      institution_name: 'HDFC',
      masked_identifier: '••••4092',
      current_book_balance_paise: 32000000,
      current_book_balance: 320000.0,
    },
    {
      id: 'acc-2',
      name: 'Zerodha Mutual Funds',
      account_type: 'investment',
      institution_name: 'Zerodha',
      masked_identifier: null,
      current_book_balance_paise: 20000000,
      current_book_balance: 200000.0,
    },
  ],
  liability_accounts: [
    {
      id: 'acc-3',
      name: 'ICICI Sapphiro Card',
      account_type: 'credit_card',
      institution_name: 'ICICI Bank',
      masked_identifier: '••••9912',
      outstanding_liability_paise: 4500000,
      outstanding_liability: 45000.0,
      credit_limit_paise: 50000000,
      credit_limit: 500000.0,
      due_date: '2026-03-05',
    },
  ],
};

const mockCashFlow = {
  currency: 'INR',
  grouping: 'month',
  start_date: '2026-01-01',
  end_date: '2026-02-28',
  trends: [
    {
      period_start: '2026-01-01',
      period_label: 'Jan 2026',
      income_paise: 14000000,
      income: 140000.0,
      expenses_paise: 7500000,
      expenses: 75000.0,
      net_cash_flow_paise: 6500000,
      net_cash_flow: 65000.0,
      cumulative_cash_flow_paise: 6500000,
      cumulative_cash_flow: 65000.0,
      transaction_count: 38,
    },
    {
      period_start: '2026-02-01',
      period_label: 'Feb 2026',
      income_paise: 15000000,
      income: 150000.0,
      expenses_paise: 8000000,
      expenses: 80000.0,
      net_cash_flow_paise: 7000000,
      net_cash_flow: 70000.0,
      cumulative_cash_flow_paise: 13500000,
      cumulative_cash_flow: 135000.0,
      transaction_count: 42,
    },
  ],
};

const mockCategorySpending = {
  direction: 'outflow',
  currency: 'INR',
  total_spend_paise: 8000000,
  total_spend: 80000.0,
  categories: [
    {
      category_id: 'cat-1',
      category_name: 'Food & Dining',
      category_slug: 'food-dining',
      icon: 'utensils',
      color: '#6366f1',
      is_system: true,
      is_uncategorized: false,
      total_amount_paise: 3500000,
      total_amount: 35000.0,
      percentage_of_total: 43.75,
      transaction_count: 20,
    },
    {
      category_id: null,
      category_name: 'Uncategorized',
      category_slug: 'uncategorized',
      icon: 'help-circle',
      color: '#94a3b8',
      is_system: false,
      is_uncategorized: true,
      total_amount_paise: 450000,
      total_amount: 4500.0,
      percentage_of_total: 5.63,
      transaction_count: 3,
    },
  ],
};

const mockMerchantSpending = {
  currency: 'INR',
  total_spend_paise: 8000000,
  total_spend: 80000.0,
  merchants: [
    {
      merchant_name: 'Swiggy',
      total_amount_paise: 1850000,
      total_amount: 18500.0,
      percentage_of_total: 23.13,
      transaction_count: 12,
      average_ticket_paise: 154166,
      average_ticket: 1541.66,
      last_transaction_date: '2026-02-12',
    },
    {
      merchant_name: 'Amazon India',
      total_amount_paise: 1200000,
      total_amount: 12000.0,
      percentage_of_total: 15.0,
      transaction_count: 4,
      average_ticket_paise: 300000,
      average_ticket: 3000.0,
      last_transaction_date: '2026-02-10',
    },
  ],
};

const mockComparison = {
  currency: 'INR',
  current_period: {
    start_date: '2026-02-01',
    end_date: '2026-02-28',
    income_paise: 15000000,
    income: 150000.0,
    expenses_paise: 8000000,
    expenses: 80000.0,
    net_cash_flow_paise: 7000000,
    net_cash_flow: 70000.0,
    savings_rate_percentage: 46.67,
  },
  previous_period: {
    start_date: '2026-01-01',
    end_date: '2026-01-31',
    income_paise: 14000000,
    income: 140000.0,
    expenses_paise: 7500000,
    expenses: 75000.0,
    net_cash_flow_paise: 6500000,
    net_cash_flow: 65000.0,
    savings_rate_percentage: 46.43,
  },
  deltas: {
    income_delta_paise: 1000000,
    income_delta: 10000.0,
    income_percentage_delta: 7.14,
    income_sentiment: 'favorable',
    expenses_delta_paise: 500000,
    expenses_delta: 5000.0,
    expenses_percentage_delta: 6.67,
    expenses_sentiment: 'unfavorable',
    net_cash_flow_delta_paise: 500000,
    net_cash_flow_delta: 5000.0,
    net_cash_flow_percentage_delta: 7.69,
    net_cash_flow_sentiment: 'favorable',
    savings_rate_delta_percentage: 0.24,
    savings_rate_sentiment: 'favorable',
  },
};

describe('Dashboard Component', () => {
  const setDatePresetMock = vi.fn();
  const setCustomDateRangeMock = vi.fn();
  const setGroupingMock = vi.fn();
  const setSelectedAccountIdMock = vi.fn();
  const fetchAnalyticsMock = vi.fn();
  const exportCSVMock = vi.fn().mockResolvedValue(new Blob(['csv,content'], { type: 'text/csv' }));
  const fetchAccountsMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (useAccountStore as any).mockReturnValue({
      accounts: [
        { id: 'acc-1', name: 'HDFC Salary Bank', account_type: 'salary' },
        { id: 'acc-3', name: 'ICICI Sapphiro Card', account_type: 'credit_card' },
      ],
      fetchAccounts: fetchAccountsMock,
    });

    (useAnalyticsStore as any).mockReturnValue({
      overview: mockOverview,
      cashFlow: mockCashFlow,
      categorySpending: mockCategorySpending,
      merchantSpending: mockMerchantSpending,
      netWorth: mockNetWorth,
      comparison: mockComparison,
      loading: false,
      error: null,
      datePreset: 'this_month',
      startDate: '2026-02-01',
      endDate: '2026-02-28',
      grouping: 'month',
      currency: 'INR',
      selectedAccountId: null,
      setDatePreset: setDatePresetMock,
      setCustomDateRange: setCustomDateRangeMock,
      setGrouping: setGroupingMock,
      setSelectedAccountId: setSelectedAccountIdMock,
      fetchAnalytics: fetchAnalyticsMock,
      exportCSV: exportCSVMock,
    });
  });

  it('renders page header and financial metrics', () => {
    render(<Dashboard />);
    expect(screen.getByText(/Financial Analytics & Insights/i)).toBeInTheDocument();
    expect(screen.getByText(/Current Net Worth/i)).toBeInTheDocument();
    expect(screen.getByText(/Operating Inflow/i)).toBeInTheDocument();
    expect(screen.getByText(/Operating Outflow/i)).toBeInTheDocument();
    expect(screen.getByText(/Net Cash Flow/i)).toBeInTheDocument();
    expect(screen.getByText(/Savings Rate: 46.67%/i)).toBeInTheDocument();
  });

  it('renders data quality indicators for uncategorized transactions and transfers', () => {
    render(<Dashboard />);
    expect(screen.getByText(/42/i)).toBeInTheDocument(); // posted txns
    expect(screen.getByText(/3 Uncategorized/i)).toBeInTheDocument();
    expect(screen.getByText(/4 Transfers Excluded/i)).toBeInTheDocument();
    expect(screen.getByText(/2 Pending Excluded/i)).toBeInTheDocument();
  });

  it('calls setDatePreset when a period preset is clicked', () => {
    render(<Dashboard />);
    const lastMonthBtn = screen.getByText('Last Month');
    fireEvent.click(lastMonthBtn);
    expect(setDatePresetMock).toHaveBeenCalledWith('last_month');
  });

  it('calls setSelectedAccountId when account filter changes', () => {
    render(<Dashboard />);
    const select = screen.getByLabelText(/Filter by Financial Account/i);
    fireEvent.change(select, { target: { value: 'acc-1' } });
    expect(setSelectedAccountIdMock).toHaveBeenCalledWith('acc-1');
  });

  it('renders top merchant ranking with transaction details', () => {
    render(<Dashboard />);
    expect(screen.getByText('Swiggy')).toBeInTheDocument();
    expect(screen.getByText('Amazon India')).toBeInTheDocument();
    expect(screen.getByText(/12 txns/i)).toBeInTheDocument();
  });

  it('renders balance sheet assets and liabilities correctly', () => {
    render(<Dashboard />);
    expect(screen.getByText(/Liquid & Investment Assets/i)).toBeInTheDocument();
    expect(screen.getByText(/Liabilities & Credit Lines/i)).toBeInTheDocument();
    expect(screen.getByText('HDFC Salary Bank')).toBeInTheDocument();
    expect(screen.getByText('ICICI Sapphiro Card')).toBeInTheDocument();
  });
});
