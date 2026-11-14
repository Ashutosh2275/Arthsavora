import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Forecast } from '../Forecast';
import { useForecastStore } from '@/store/useForecastStore';

vi.mock('@/store/useForecastStore');

const mockCashFlow = {
  workspace_id: 'ws-1',
  forecast_run_id: 'run-1',
  horizon_days: 30,
  resolution: 'daily',
  currency: 'INR',
  starting_balance_paise: 5000000,
  starting_balance: 50000,
  projected_ending_balance_paise: 6500000,
  projected_ending_balance: 65000,
  total_projected_inflow_paise: 10000000,
  total_projected_inflow: 100000,
  total_projected_outflow_paise: 8500000,
  total_projected_outflow: 85000,
  net_cash_flow_paise: 1500000,
  net_cash_flow: 15000,
  model_name: 'holt_winters',
  model_version: 'v1.0.0',
  data_quality_score: 1.0,
  status: 'completed',
  timeline: [
    {
      date: '2026-11-15',
      starting_balance_paise: 5000000,
      inflow_paise: 500000,
      inflow_recurring_paise: 500000,
      outflow_paise: 200000,
      outflow_recurring_paise: 100000,
      net_cash_flow_paise: 300000,
      projected_balance_paise: 5300000,
      lower_balance_paise: 5100000,
      upper_balance_paise: 5500000,
    },
  ],
  created_at: '2026-11-14T00:00:00Z',
};

const mockIncome = {
  workspace_id: 'ws-1',
  forecast_run_id: 'run-1',
  horizon_days: 30,
  total_expected_income_paise: 10000000,
  total_expected_income: 100000,
  scheduled_income_paise: 8000000,
  scheduled_income: 80000,
  estimated_discretionary_income_paise: 2000000,
  estimated_discretionary_income: 20000,
  model_used: 'holt_winters',
  points: [],
};

const mockExpense = {
  workspace_id: 'ws-1',
  forecast_run_id: 'run-1',
  horizon_days: 30,
  total_expected_expense_paise: 8500000,
  total_expected_expense: 85000,
  scheduled_commitments_paise: 5000000,
  scheduled_commitments: 50000,
  discretionary_expense_paise: 3500000,
  discretionary_expense: 35000,
  model_used: 'holt_winters',
  points: [],
};

const mockCategoryForecast = {
  workspace_id: 'ws-1',
  forecast_run_id: 'run-1',
  horizon_days: 30,
  categories: [
    {
      category_id: 'cat-1',
      category_name: 'Rent & Housing',
      projected_amount_paise: 2500000,
      projected_amount: 25000,
      lower_amount_paise: 2400000,
      lower_amount: 24000,
      upper_amount_paise: 2600000,
      upper_amount: 26000,
      historical_monthly_average_paise: 2500000,
      historical_monthly_average: 25000,
      trend_direction: 'stable',
    },
  ],
};

const mockBudgetExhaustion = {
  workspace_id: 'ws-1',
  as_of_date: '2026-11-14',
  estimates: [
    {
      budget_id: 'b-1',
      budget_name: 'November Operations',
      category_id: null,
      category_name: 'Overall Budget',
      total_allocated_paise: 5000000,
      total_allocated: 50000,
      current_spend_paise: 3500000,
      current_spend: 35000,
      remaining_paise: 1500000,
      remaining: 15000,
      burn_rate_daily_paise: 250000,
      burn_rate_daily: 2500,
      utilization_pct: 70.0,
      estimated_exhaustion_date: '2026-11-20',
      days_to_exhaustion: 6,
      status: 'projected_exhaustion',
    },
  ],
};

const mockGoalTrajectories = {
  workspace_id: 'ws-1',
  as_of_date: '2026-11-14',
  goals: [
    {
      goal_id: 'g-1',
      goal_name: 'Emergency Fund',
      target_amount_paise: 30000000,
      target_amount: 300000,
      current_balance_paise: 15000000,
      current_balance: 150000,
      remaining_paise: 15000000,
      remaining: 150000,
      target_date: '2027-05-01',
      monthly_savings_pace_paise: 2500000,
      monthly_savings_pace: 25000,
      projected_completion_date: '2027-04-15',
      is_on_track: true,
      status: 'on_track',
    },
  ],
};

const mockScenarios = [
  {
    id: 'scen-1',
    workspace_id: 'ws-1',
    name: '10% Salary Hike Simulation',
    description: 'Models effect of 10% raise',
    scenario_type: 'optimistic',
    horizon_days: 30,
    assumptions: {
      income_change_pct: 10,
      expense_change_pct: 0,
    },
    results: {
      scenario_projected_balance_paise: 7500000,
      delta_balance_paise: 1000000,
    },
    created_at: '2026-11-14T00:00:00Z',
  },
];

const mockEvaluations = [
  {
    id: 'eval-1',
    workspace_id: 'ws-1',
    model_name: 'holt_winters',
    metric_type: 'expense',
    horizon_days: 30,
    mae_paise: 12000,
    mae: 120,
    rmse_paise: 18000,
    rmse: 180,
    wape: 0.085,
    bias_paise: 500,
    bias: 5,
    interval_coverage: 0.82,
    sample_size: 45,
    is_best_model: true,
    created_at: '2026-11-14T00:00:00Z',
  },
];

describe('Financial Forecasting & Scenarios Page', () => {
  const mockFetchOverview = vi.fn();
  const mockFetchBudgetExhaustion = vi.fn();
  const mockFetchGoalTrajectories = vi.fn();
  const mockFetchScenarios = vi.fn();
  const mockFetchEvaluations = vi.fn();
  const mockGenerateForecast = vi.fn();
  const mockCreateScenario = vi.fn();
  const mockDeleteScenario = vi.fn();
  const mockSetSelectedHorizon = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useForecastStore).mockReturnValue({
      cashFlowForecast: mockCashFlow,
      incomeForecast: mockIncome,
      expenseForecast: mockExpense,
      categoryForecast: mockCategoryForecast,
      budgetExhaustion: mockBudgetExhaustion,
      goalTrajectories: mockGoalTrajectories,
      scenarios: mockScenarios,
      evaluations: mockEvaluations,
      selectedHorizon: 30,
      isLoading: false,
      error: null,
      setSelectedHorizon: mockSetSelectedHorizon,
      fetchForecastOverview: mockFetchOverview,
      generateForecast: mockGenerateForecast,
      fetchBudgetExhaustion: mockFetchBudgetExhaustion,
      fetchGoalTrajectories: mockFetchGoalTrajectories,
      fetchScenarios: mockFetchScenarios,
      createScenario: mockCreateScenario,
      deleteScenario: mockDeleteScenario,
      fetchEvaluations: mockFetchEvaluations,
    });
  });

  it('renders page header and summary KPI metrics', () => {
    render(<Forecast />);

    expect(screen.getByText('Financial Forecasting & Predictive Intelligence')).toBeInTheDocument();
    expect(screen.getByText('Starting Liquid Balance')).toBeInTheDocument();
    expect(screen.getByText('Projected Ending Balance')).toBeInTheDocument();
    expect(screen.getByText('Net Cash Flow Outlook')).toBeInTheDocument();
  });

  it('switches between tabs cleanly', () => {
    render(<Forecast />);

    // Switch to Income & Category Breakdown
    const categoryTab = screen.getByRole('button', { name: /Income & Category Breakdown/i });
    fireEvent.click(categoryTab);
    expect(screen.getByText('Category-Wise Spending Forecasts')).toBeInTheDocument();

    // Switch to Budget Exhaustion & Goals
    const budgetTab = screen.getByRole('button', { name: /Budget Exhaustion & Goals/i });
    fireEvent.click(budgetTab);
    expect(screen.getByText('Budget Exhaustion Estimates')).toBeInTheDocument();
    expect(screen.getByText('Savings Goal Completion Trajectories')).toBeInTheDocument();

    // Switch to Scenarios
    const scenarioTab = screen.getByRole('button', { name: /What-If Scenarios/i });
    fireEvent.click(scenarioTab);
    expect(screen.getByText('Deterministic What-If Scenarios')).toBeInTheDocument();
    expect(screen.getByText('10% Salary Hike Simulation')).toBeInTheDocument();
  });

  it('renders cash-flow progression table', () => {
    render(<Forecast />);

    expect(screen.getByText(/Forward Cash-Flow Progression/i)).toBeInTheDocument();
    expect(screen.getByText('Confidence Band (Lower – Upper)')).toBeInTheDocument();
  });

  it('opens and closes the scenario builder modal', () => {
    render(<Forecast />);

    const newScenarioBtn = screen.getByRole('button', { name: /New Scenario/i });
    fireEvent.click(newScenarioBtn);

    expect(screen.getByText('Build Financial What-If Scenario')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/10% Salary Hike/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Build Financial What-If Scenario')).not.toBeInTheDocument();
  });

  it('allows switching forecast horizon', () => {
    render(<Forecast />);

    const sevenDayBtn = screen.getByRole('button', { name: '7D' });
    fireEvent.click(sevenDayBtn);

    expect(mockSetSelectedHorizon).toHaveBeenCalledWith(7);
    expect(mockFetchOverview).toHaveBeenCalledWith(7);
  });
});
