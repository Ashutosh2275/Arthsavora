import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Budgets from '../Budgets';
import { useBudgetStore } from '@/store/useBudgetStore';
import { useCategoryStore } from '@/store/useCategoryStore';

vi.mock('@/store/useBudgetStore');
vi.mock('@/store/useCategoryStore');

const mockBudgetProgress = {
  budget_id: 'b-1',
  name: 'November 2026 Household Budget',
  currency: 'INR',
  start_date: '2026-11-01',
  end_date: '2026-11-30',
  as_of_date: '2026-11-14',
  total_allocated_paise: 5000000,
  total_allocated_amount: '50000.00',
  total_spent_paise: 2450000,
  total_spent_amount: '24500.00',
  remaining_paise: 2550000,
  remaining_amount: '25500.00',
  utilization_percentage: 49.0,
  overspent: false,
  warning_state: 'normal',
  period_days: 30,
  elapsed_days: 14,
  remaining_days: 16,
  period_elapsed_percentage: 46.67,
  linear_projection: {
    days_in_period: 30,
    elapsed_days: 14,
    remaining_days: 16,
    daily_run_rate_paise: 175000,
    daily_run_rate: '1750.00',
    projected_period_end_spend_paise: 5250000,
    projected_period_end_spend: '52500.00',
    projected_variance_paise: 250000,
    projected_variance: '2500.00',
    projected_overspent: true,
    methodology: 'linear_extrapolation',
    assumptions: 'Disclosed test assumption',
  },
  allocations: [
    {
      allocation_id: 'alloc-1',
      category_id: 'cat-1',
      category_name: 'Groceries & Provisions',
      category_color: '#10b981',
      allocated_paise: 2000000,
      allocated_amount: '20000.00',
      spent_paise: 1200000,
      spent_amount: '12000.00',
      remaining_paise: 800000,
      remaining_amount: '8000.00',
      utilization_percentage: 60.0,
      overspent: false,
      warning_state: 'normal',
      warning_threshold_percentage: 80,
    },
  ],
  unallocated_capacity_paise: 3000000,
  unallocated_capacity_amount: '30000.00',
  new_alerts_triggered: 0,
};

const mockBudgetDetail = {
  id: 'b-1',
  workspace_id: 'ws-1',
  name: 'November 2026 Household Budget',
  budget_type: 'monthly',
  currency: 'INR',
  start_date: '2026-11-01',
  end_date: '2026-11-30',
  total_allocated_paise: 5000000,
  total_allocated: '50000.00',
  recurrence_interval: 'monthly',
  status: 'active',
  allocations_count: 1,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  allocations: [],
  settings: {},
};

describe('Budgets Page Component', () => {
  const mockFetchBudgets = vi.fn();
  const mockSelectBudget = vi.fn();
  const mockCreateBudget = vi.fn();
  const mockFetchCategories = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useBudgetStore).mockReturnValue({
      budgets: [mockBudgetDetail],
      selectedBudget: mockBudgetDetail,
      budgetProgress: mockBudgetProgress,
      revisions: [],
      alerts: [],
      loading: false,
      progressLoading: false,
      error: null,
      fetchBudgets: mockFetchBudgets,
      selectBudget: mockSelectBudget,
      createBudget: mockCreateBudget,
      updateBudget: vi.fn(),
      deleteBudget: vi.fn(),
      rolloverBudget: vi.fn(),
      addAllocation: vi.fn(),
      updateAllocation: vi.fn(),
      removeAllocation: vi.fn(),
      fetchProgress: vi.fn(),
      fetchRevisions: vi.fn(),
      fetchAlerts: vi.fn(),
    });

    vi.mocked(useCategoryStore).mockReturnValue({
      categories: [
        {
          id: 'cat-1',
          workspace_id: 'ws-1',
          name: 'Groceries & Provisions',
          code: 'GROCERY',
          category_type: 'expense',
          color: '#10b981',
          icon: 'shopping-cart',
          is_system: false,
          is_active: true,
          parent_id: null,
          metadata_payload: {},
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      fetchCategories: mockFetchCategories,
    } as any);
  });

  it('renders budget page title and fetches initial budgets and categories', () => {
    render(<Budgets />);
    expect(screen.getByText('Personal Budgeting & Spending Controls')).toBeInTheDocument();
    expect(mockFetchBudgets).toHaveBeenCalled();
    expect(mockFetchCategories).toHaveBeenCalled();
  });

  it('renders budget KPI metric cards correctly', () => {
    render(<Budgets />);
    expect(screen.getByText('Total Allocated')).toBeInTheDocument();
    expect(screen.getByText('Actual Spent')).toBeInTheDocument();
    expect(screen.getByText('Remaining Capacity')).toBeInTheDocument();
    expect(screen.getByText('Projected Period-End')).toBeInTheDocument();
  });

  it('displays category spending allocations', () => {
    render(<Budgets />);
    expect(screen.getByText('Groceries & Provisions')).toBeInTheDocument();
    expect(screen.getByText('Category Spending Allocations (1)')).toBeInTheDocument();
  });

  it('opens create budget modal when clicking Create Budget button', () => {
    render(<Budgets />);
    const createBtn = screen.getByText('Create Budget');
    fireEvent.click(createBtn);
    expect(screen.getByText('Establish New Personal Budget')).toBeInTheDocument();
  });
});
