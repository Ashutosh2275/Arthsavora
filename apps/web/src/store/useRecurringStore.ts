import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  CashFlowCommitmentsResponse,
  OccurrenceConfirmRequest,
  OccurrenceMatchRequest,
  OccurrenceResponse,
  OccurrenceSkipRequest,
  RecurringDefinitionCreateRequest,
  RecurringDefinitionResponse,
  RecurringDefinitionUpdateRequest,
  RecurringDetectRequest,
  RecurringSuggestionResponse,
  SuggestionConfirmRequest,
  SuggestionDismissRequest,
} from '@arthsavora/contracts';

interface RecurringState {
  definitions: RecurringDefinitionResponse[];
  commitments: CashFlowCommitmentsResponse | null;
  occurrences: OccurrenceResponse[];
  suggestions: RecurringSuggestionResponse[];
  loading: boolean;
  commitmentsLoading: boolean;
  detecting: boolean;
  error: string | null;

  fetchDefinitions: (status?: string, direction?: string) => Promise<void>;
  createDefinition: (payload: RecurringDefinitionCreateRequest) => Promise<RecurringDefinitionResponse | null>;
  updateDefinition: (id: string, payload: RecurringDefinitionUpdateRequest) => Promise<boolean>;
  pauseDefinition: (id: string) => Promise<boolean>;
  resumeDefinition: (id: string) => Promise<boolean>;
  cancelDefinition: (id: string) => Promise<boolean>;

  fetchOccurrences: (params?: { recurring_id?: string; status?: string; start_date?: string; end_date?: string }) => Promise<void>;
  skipOccurrence: (id: string, reason?: string) => Promise<boolean>;
  confirmOccurrence: (id: string, notes?: string) => Promise<boolean>;
  matchOccurrence: (id: string, transactionId: string, notes?: string) => Promise<boolean>;
  unmatchOccurrence: (id: string) => Promise<boolean>;

  fetchCommitments: (windowDays?: number, startDate?: string) => Promise<void>;
  fetchSuggestions: (status?: string) => Promise<void>;
  runDetection: (lookbackDays?: number) => Promise<void>;
  confirmSuggestion: (id: string, payload: SuggestionConfirmRequest) => Promise<boolean>;
  dismissSuggestion: (id: string, reason?: string) => Promise<boolean>;
}

export const useRecurringStore = create<RecurringState>((set, get) => ({
  definitions: [],
  commitments: null,
  occurrences: [],
  suggestions: [],
  loading: false,
  commitmentsLoading: false,
  detecting: false,
  error: null,

  fetchDefinitions: async (status, direction) => {
    set({ loading: true, error: null });
    try {
      const res = await api.get<{ status: string; data: RecurringDefinitionResponse[] }>('/v1/recurring', {
        params: { ...(status ? { status } : {}), ...(direction ? { direction } : {}) },
      });
      set({ definitions: res.data?.data || [], loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to load recurring activities', loading: false });
    }
  },

  createDefinition: async (payload) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<{ status: string; data: RecurringDefinitionResponse }>('/v1/recurring', payload);
      const created = res.data?.data;
      if (created) {
        set((state) => ({ definitions: [created, ...state.definitions], loading: false }));
        // Refresh commitments
        get().fetchCommitments();
      }
      return created;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to create recurring activity', loading: false });
      return null;
    }
  },

  updateDefinition: async (id, payload) => {
    set({ loading: true, error: null });
    try {
      const res = await api.patch<{ status: string; data: RecurringDefinitionResponse }>(`/v1/recurring/${id}`, payload);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          definitions: state.definitions.map((d) => (d.id === id ? updated : d)),
          loading: false,
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to update recurring activity', loading: false });
      return false;
    }
  },

  pauseDefinition: async (id) => {
    try {
      const res = await api.post<{ status: string; data: RecurringDefinitionResponse }>(`/v1/recurring/${id}/pause`);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          definitions: state.definitions.map((d) => (d.id === id ? updated : d)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to pause recurring schedule' });
      return false;
    }
  },

  resumeDefinition: async (id) => {
    try {
      const res = await api.post<{ status: string; data: RecurringDefinitionResponse }>(`/v1/recurring/${id}/resume`);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          definitions: state.definitions.map((d) => (d.id === id ? updated : d)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to resume recurring schedule' });
      return false;
    }
  },

  cancelDefinition: async (id) => {
    try {
      const res = await api.post<{ status: string; data: RecurringDefinitionResponse }>(`/v1/recurring/${id}/cancel`);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          definitions: state.definitions.map((d) => (d.id === id ? updated : d)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to cancel recurring schedule' });
      return false;
    }
  },

  fetchOccurrences: async (params) => {
    try {
      const res = await api.get<{ status: string; data: OccurrenceResponse[] }>('/v1/recurring/occurrences/list', {
        params,
      });
      set({ occurrences: res.data?.data || [] });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to load occurrences' });
    }
  },

  skipOccurrence: async (id, reason) => {
    try {
      const res = await api.post<{ status: string; data: OccurrenceResponse }>(`/v1/recurring/occurrences/${id}/skip`, {
        reason,
      });
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          occurrences: state.occurrences.map((o) => (o.id === id ? updated : o)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to skip occurrence' });
      return false;
    }
  },

  confirmOccurrence: async (id, notes) => {
    try {
      const res = await api.post<{ status: string; data: OccurrenceResponse }>(`/v1/recurring/occurrences/${id}/confirm`, {
        notes,
      });
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          occurrences: state.occurrences.map((o) => (o.id === id ? updated : o)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to confirm occurrence' });
      return false;
    }
  },

  matchOccurrence: async (id, transactionId, notes) => {
    try {
      const res = await api.post<{ status: string; data: OccurrenceResponse }>(`/v1/recurring/occurrences/${id}/match`, {
        transaction_id: transactionId,
        notes,
      });
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          occurrences: state.occurrences.map((o) => (o.id === id ? updated : o)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to match occurrence' });
      return false;
    }
  },

  unmatchOccurrence: async (id) => {
    try {
      const res = await api.post<{ status: string; data: OccurrenceResponse }>(`/v1/recurring/occurrences/${id}/unmatch`);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          occurrences: state.occurrences.map((o) => (o.id === id ? updated : o)),
        }));
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to unmatch occurrence' });
      return false;
    }
  },

  fetchCommitments: async (windowDays = 30, startDate) => {
    set({ commitmentsLoading: true });
    try {
      const res = await api.get<{ status: string; data: CashFlowCommitmentsResponse }>('/v1/recurring/commitments/overview', {
        params: { window_days: windowDays, ...(startDate ? { start_date: startDate } : {}) },
      });
      set({ commitments: res.data?.data || null, commitmentsLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to load commitments', commitmentsLoading: false });
    }
  },

  fetchSuggestions: async (status = 'pending') => {
    try {
      const res = await api.get<{ status: string; data: RecurringSuggestionResponse[] }>('/v1/recurring/suggestions/list', {
        params: { status },
      });
      set({ suggestions: res.data?.data || [] });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to load suggestions' });
    }
  },

  runDetection: async (lookbackDays = 180) => {
    set({ detecting: true });
    try {
      const res = await api.post<{ status: string; data: RecurringSuggestionResponse[] }>('/v1/recurring/detect', {
        lookback_days: lookbackDays,
      });
      set({ suggestions: res.data?.data || [], detecting: false });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to run pattern detection', detecting: false });
    }
  },

  confirmSuggestion: async (id, payload) => {
    try {
      const res = await api.post<{ status: string; data: RecurringSuggestionResponse }>(`/v1/recurring/suggestions/${id}/confirm`, payload);
      if (res.data?.data) {
        set((state) => ({
          suggestions: state.suggestions.filter((s) => s.id !== id),
        }));
        get().fetchDefinitions();
        get().fetchCommitments();
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to confirm suggestion' });
      return false;
    }
  },

  dismissSuggestion: async (id, reason) => {
    try {
      const res = await api.post<{ status: string; data: RecurringSuggestionResponse }>(`/v1/recurring/suggestions/${id}/dismiss`, {
        reason,
      });
      if (res.data?.data) {
        set((state) => ({
          suggestions: state.suggestions.filter((s) => s.id !== id),
        }));
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to dismiss suggestion' });
      return false;
    }
  },
}));
