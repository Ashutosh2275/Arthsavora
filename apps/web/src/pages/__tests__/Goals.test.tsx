import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Goals from '../Goals';
import { useGoalStore } from '@/store/useGoalStore';

vi.mock('@/store/useGoalStore');

const mockGoals = [
  {
    id: 'g-1',
    workspace_id: 'ws-1',
    name: 'Emergency Reserve Fund',
    description: '6 months liquid living expenses',
    goal_type: 'emergency_fund',
    currency: 'INR',
    target_amount_paise: 30000000,
    target_amount: '300000.00',
    current_amount_paise: 15000000,
    current_amount: '150000.00',
    start_date: '2026-01-01',
    target_date: '2026-12-31',
    status: 'active',
    priority: 'high',
    color: '#10b981',
    icon: 'shield',
    created_by_id: 'u-1',
    metadata_payload: {},
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('Goals Page Component', () => {
  const mockFetchGoals = vi.fn();
  const mockCreateGoal = vi.fn();
  const mockRecordContribution = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useGoalStore).mockReturnValue({
      goals: mockGoals,
      selectedGoal: mockGoals[0],
      selectedGoalProgress: null,
      activities: [],
      loading: false,
      activitiesLoading: false,
      error: null,
      fetchGoals: mockFetchGoals,
      selectGoal: vi.fn(),
      createGoal: mockCreateGoal,
      updateGoal: vi.fn(),
      deleteGoal: vi.fn(),
      recordContribution: mockRecordContribution,
      recordWithdrawal: vi.fn(),
      fetchGoalProgress: vi.fn(),
      fetchActivities: vi.fn(),
    });
  });

  it('renders goals page title and fetches goals list', () => {
    render(<Goals />);
    expect(screen.getByText('Financial Goals & Milestone Tracking')).toBeInTheDocument();
    expect(mockFetchGoals).toHaveBeenCalled();
  });

  it('renders summary KPI statistics', () => {
    render(<Goals />);
    expect(screen.getByText('Total Target Capital')).toBeInTheDocument();
    expect(screen.getByText('Total Accumulated')).toBeInTheDocument();
    expect(screen.getByText('Remaining to Fund')).toBeInTheDocument();
    expect(screen.getByText('Active Goals')).toBeInTheDocument();
  });

  it('displays the list of goals and funding progress', () => {
    render(<Goals />);
    expect(screen.getByText('Emergency Reserve Fund')).toBeInTheDocument();
    expect(screen.getByText('50.0% funded')).toBeInTheDocument();
  });

  it('opens establish new goal modal when clicking button', () => {
    render(<Goals />);
    const addBtn = screen.getByText('Establish New Goal');
    fireEvent.click(addBtn);
    expect(screen.getByText('Establish Financial Savings Goal')).toBeInTheDocument();
  });

  it('opens contribution modal when clicking Contribute', () => {
    render(<Goals />);
    const contributeBtn = screen.getByText('Contribute');
    fireEvent.click(contributeBtn);
    expect(screen.getByText('Contribute to Emergency Reserve Fund')).toBeInTheDocument();
  });
});
