import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  GoalActivityRequest,
  GoalActivityResponse,
  GoalCreateRequest,
  GoalProgressResponse,
  GoalResponse,
  GoalUpdateRequest,
} from '@arthsavora/contracts';

interface GoalState {
  goals: GoalResponse[];
  selectedGoal: GoalResponse | null;
  selectedGoalProgress: GoalProgressResponse | null;
  activities: GoalActivityResponse[];
  loading: boolean;
  activitiesLoading: boolean;
  error: string | null;

  fetchGoals: (statusFilter?: string, goalType?: string) => Promise<void>;
  selectGoal: (goalId: string) => Promise<void>;
  createGoal: (payload: GoalCreateRequest) => Promise<GoalResponse | null>;
  updateGoal: (goalId: string, payload: GoalUpdateRequest) => Promise<boolean>;
  deleteGoal: (goalId: string) => Promise<boolean>;
  recordContribution: (goalId: string, payload: GoalActivityRequest) => Promise<boolean>;
  recordWithdrawal: (goalId: string, payload: GoalActivityRequest) => Promise<boolean>;
  fetchGoalProgress: (goalId: string) => Promise<void>;
  fetchActivities: (goalId: string) => Promise<void>;
}

export const useGoalStore = create<GoalState>((set, get) => ({
  goals: [],
  selectedGoal: null,
  selectedGoalProgress: null,
  activities: [],
  loading: false,
  activitiesLoading: false,
  error: null,

  fetchGoals: async (statusFilter, goalType) => {
    set({ loading: true, error: null });
    try {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      if (goalType) params.goal_type = goalType;

      const res = await api.get<{ success: boolean; data: GoalResponse[] }>('/v1/goals', { params });
      const list = res.data?.data || [];
      set({ goals: list, loading: false });

      const currentSelected = get().selectedGoal;
      if (!currentSelected && list.length > 0) {
        await get().selectGoal(list[0].id);
      }
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to fetch financial goals',
      });
    }
  },

  selectGoal: async (goalId: string) => {
    set({ loading: true, error: null });
    try {
      const res = await api.get<{ success: boolean; data: GoalResponse }>(`/v1/goals/${goalId}`);
      const goal = res.data?.data;
      set({ selectedGoal: goal, loading: false });

      if (goal) {
        await Promise.allSettled([
          get().fetchGoalProgress(goalId),
          get().fetchActivities(goalId),
        ]);
      }
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to load goal details',
      });
    }
  },

  createGoal: async (payload: GoalCreateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<{ success: boolean; data: GoalResponse }>('/v1/goals', payload);
      const newGoal = res.data?.data;
      await get().fetchGoals();
      if (newGoal) {
        await get().selectGoal(newGoal.id);
      }
      return newGoal;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to create goal',
      });
      return null;
    }
  },

  updateGoal: async (goalId: string, payload: GoalUpdateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.patch<{ success: boolean; data: GoalResponse }>(`/v1/goals/${goalId}`, payload);
      const updated = res.data?.data;
      set({ selectedGoal: updated, loading: false });
      await get().fetchGoals();
      await get().fetchGoalProgress(goalId);
      return true;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to update goal',
      });
      return false;
    }
  },

  deleteGoal: async (goalId: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/v1/goals/${goalId}`);
      set({ selectedGoal: null, selectedGoalProgress: null, activities: [] });
      await get().fetchGoals();
      return true;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to delete goal',
      });
      return false;
    }
  },

  recordContribution: async (goalId: string, payload: GoalActivityRequest) => {
    try {
      await api.post<{ success: boolean; data: GoalActivityResponse }>(
        `/v1/goals/${goalId}/contributions`,
        payload
      );
      await get().selectGoal(goalId);
      await get().fetchGoals();
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to record contribution' });
      return false;
    }
  },

  recordWithdrawal: async (goalId: string, payload: GoalActivityRequest) => {
    try {
      await api.post<{ success: boolean; data: GoalActivityResponse }>(
        `/v1/goals/${goalId}/withdrawals`,
        payload
      );
      await get().selectGoal(goalId);
      await get().fetchGoals();
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to record withdrawal' });
      return false;
    }
  },

  fetchGoalProgress: async (goalId: string) => {
    try {
      const res = await api.get<{ success: boolean; data: GoalProgressResponse }>(
        `/v1/goals/${goalId}/progress`
      );
      set({ selectedGoalProgress: res.data?.data || null });
    } catch {
      // Non-critical, ignore
    }
  },

  fetchActivities: async (goalId: string) => {
    set({ activitiesLoading: true });
    try {
      const res = await api.get<{ success: boolean; data: GoalActivityResponse[] }>(
        `/v1/goals/${goalId}/activity`
      );
      set({ activities: res.data?.data || [], activitiesLoading: false });
    } catch {
      set({ activitiesLoading: false });
    }
  },
}));
