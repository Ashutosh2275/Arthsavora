import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  AllocationCreateRequest,
  AllocationUpdateRequest,
  BudgetAllocationResponse,
  BudgetAlertResponse,
  BudgetCreateRequest,
  BudgetDetailResponse,
  BudgetProgressResponse,
  BudgetRevisionResponse,
  BudgetRolloverRequest,
  BudgetSummaryResponse,
  BudgetUpdateRequest,
} from '@arthsavora/contracts';

interface BudgetState {
  budgets: BudgetSummaryResponse[];
  selectedBudget: BudgetDetailResponse | null;
  budgetProgress: BudgetProgressResponse | null;
  revisions: BudgetRevisionResponse[];
  alerts: BudgetAlertResponse[];
  loading: boolean;
  progressLoading: boolean;
  error: string | null;

  fetchBudgets: (status?: string) => Promise<void>;
  selectBudget: (budgetId: string) => Promise<void>;
  createBudget: (payload: BudgetCreateRequest) => Promise<BudgetDetailResponse | null>;
  updateBudget: (budgetId: string, payload: BudgetUpdateRequest) => Promise<boolean>;
  deleteBudget: (budgetId: string, reason?: string) => Promise<boolean>;
  fetchProgress: (budgetId: string, asOfDate?: string) => Promise<void>;
  fetchRevisions: (budgetId: string) => Promise<void>;
  fetchAlerts: (budgetId: string) => Promise<void>;
  rolloverBudget: (budgetId: string, payload: BudgetRolloverRequest) => Promise<BudgetDetailResponse | null>;
  addAllocation: (budgetId: string, payload: AllocationCreateRequest) => Promise<boolean>;
  updateAllocation: (budgetId: string, allocationId: string, payload: AllocationUpdateRequest) => Promise<boolean>;
  removeAllocation: (budgetId: string, allocationId: string, reason?: string) => Promise<boolean>;
}

export const useBudgetStore = create<BudgetState>((set, get) => ({
  budgets: [],
  selectedBudget: null,
  budgetProgress: null,
  revisions: [],
  alerts: [],
  loading: false,
  progressLoading: false,
  error: null,

  fetchBudgets: async (statusFilter) => {
    set({ loading: true, error: null });
    try {
      const res = await api.get<{ success: boolean; data: BudgetSummaryResponse[] }>('/v1/budgets', {
        params: statusFilter ? { status: statusFilter } : {},
      });
      const list = res.data?.data || [];
      set({ budgets: list, loading: false });

      // Automatically select first active budget if none selected
      const currentSelected = get().selectedBudget;
      if (!currentSelected && list.length > 0) {
        await get().selectBudget(list[0].id);
      }
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to fetch budgets',
      });
    }
  },

  selectBudget: async (budgetId: string) => {
    set({ loading: true, error: null });
    try {
      const res = await api.get<{ success: boolean; data: BudgetDetailResponse }>(`/v1/budgets/${budgetId}`);
      const detail = res.data?.data;
      set({ selectedBudget: detail, loading: false });
      if (detail) {
        // Concurrently fetch progress, revisions, and alerts
        await Promise.allSettled([
          get().fetchProgress(budgetId),
          get().fetchRevisions(budgetId),
          get().fetchAlerts(budgetId),
        ]);
      }
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to load budget details',
      });
    }
  },

  createBudget: async (payload: BudgetCreateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<{ success: boolean; data: BudgetDetailResponse }>('/v1/budgets', payload);
      const newBudget = res.data?.data;
      await get().fetchBudgets();
      if (newBudget) {
        await get().selectBudget(newBudget.id);
      }
      return newBudget;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to create budget',
      });
      return null;
    }
  },

  updateBudget: async (budgetId: string, payload: BudgetUpdateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.patch<{ success: boolean; data: BudgetDetailResponse }>(`/v1/budgets/${budgetId}`, payload);
      const updated = res.data?.data;
      set({ selectedBudget: updated, loading: false });
      await get().fetchBudgets();
      await get().fetchProgress(budgetId);
      return true;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to update budget',
      });
      return false;
    }
  },

  deleteBudget: async (budgetId: string, reason?: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/v1/budgets/${budgetId}`, {
        params: reason ? { reason } : {},
      });
      set({ selectedBudget: null, budgetProgress: null });
      await get().fetchBudgets();
      return true;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to delete budget',
      });
      return false;
    }
  },

  fetchProgress: async (budgetId: string, asOfDate?: string) => {
    set({ progressLoading: true });
    try {
      const res = await api.get<{ success: boolean; data: BudgetProgressResponse }>(
        `/v1/budgets/${budgetId}/progress`,
        { params: asOfDate ? { as_of_date: asOfDate } : {} }
      );
      set({ budgetProgress: res.data?.data || null, progressLoading: false });
    } catch (err: any) {
      set({
        progressLoading: false,
        error: err.response?.data?.message || err.message || 'Failed to evaluate budget progress',
      });
    }
  },

  fetchRevisions: async (budgetId: string) => {
    try {
      const res = await api.get<{ success: boolean; data: BudgetRevisionResponse[] }>(
        `/v1/budgets/${budgetId}/revisions`
      );
      set({ revisions: res.data?.data || [] });
    } catch {
      // Non-critical, ignore
    }
  },

  fetchAlerts: async (budgetId: string) => {
    try {
      const res = await api.get<{ success: boolean; data: BudgetAlertResponse[] }>(
        `/v1/budgets/${budgetId}/alerts`
      );
      set({ alerts: res.data?.data || [] });
    } catch {
      // Non-critical, ignore
    }
  },

  rolloverBudget: async (budgetId: string, payload: BudgetRolloverRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<{ success: boolean; data: BudgetDetailResponse }>(
        `/v1/budgets/${budgetId}/rollover`,
        payload
      );
      const newBudget = res.data?.data;
      await get().fetchBudgets();
      if (newBudget) {
        await get().selectBudget(newBudget.id);
      }
      return newBudget;
    } catch (err: any) {
      set({
        loading: false,
        error: err.response?.data?.message || err.message || 'Failed to roll over budget',
      });
      return null;
    }
  },

  addAllocation: async (budgetId: string, payload: AllocationCreateRequest) => {
    try {
      const res = await api.post<{ success: boolean; data: BudgetDetailResponse }>(
        `/v1/budgets/${budgetId}/allocations`,
        payload
      );
      set({ selectedBudget: res.data?.data });
      await get().fetchProgress(budgetId);
      await get().fetchRevisions(budgetId);
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to add allocation' });
      return false;
    }
  },

  updateAllocation: async (budgetId: string, allocationId: string, payload: AllocationUpdateRequest) => {
    try {
      const res = await api.patch<{ success: boolean; data: BudgetDetailResponse }>(
        `/v1/budgets/${budgetId}/allocations/${allocationId}`,
        payload
      );
      set({ selectedBudget: res.data?.data });
      await get().fetchProgress(budgetId);
      await get().fetchRevisions(budgetId);
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to update allocation' });
      return false;
    }
  },

  removeAllocation: async (budgetId: string, allocationId: string, reason?: string) => {
    try {
      const res = await api.delete<{ success: boolean; data: BudgetDetailResponse }>(
        `/v1/budgets/${budgetId}/allocations/${allocationId}`,
        { params: reason ? { reason } : {} }
      );
      set({ selectedBudget: res.data?.data });
      await get().fetchProgress(budgetId);
      await get().fetchRevisions(budgetId);
      return true;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to remove allocation' });
      return false;
    }
  },
}));
