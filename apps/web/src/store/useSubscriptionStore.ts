import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  SubscriptionCreateRequest,
  SubscriptionResponse,
  SubscriptionUpdateRequest,
} from '@arthsavora/contracts';

interface SubscriptionState {
  subscriptions: SubscriptionResponse[];
  loading: boolean;
  error: string | null;

  fetchSubscriptions: (status?: string) => Promise<void>;
  createSubscription: (payload: SubscriptionCreateRequest) => Promise<SubscriptionResponse | null>;
  updateSubscription: (id: string, payload: SubscriptionUpdateRequest) => Promise<boolean>;
  cancelSubscription: (id: string) => Promise<boolean>;
}

export const useSubscriptionStore = create<SubscriptionState>((set, get) => ({
  subscriptions: [],
  loading: false,
  error: null,

  fetchSubscriptions: async (status) => {
    set({ loading: true, error: null });
    try {
      const res = await api.get<{ status: string; data: SubscriptionResponse[] }>('/v1/recurring/subscriptions/list', {
        params: status ? { status } : {},
      });
      set({ subscriptions: res.data?.data || [], loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to load subscriptions', loading: false });
    }
  },

  createSubscription: async (payload) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post<{ status: string; data: SubscriptionResponse }>('/v1/recurring/subscriptions/create', payload);
      const created = res.data?.data;
      if (created) {
        set((state) => ({ subscriptions: [created, ...state.subscriptions], loading: false }));
      }
      return created;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to create subscription', loading: false });
      return null;
    }
  },

  updateSubscription: async (id, payload) => {
    set({ loading: true, error: null });
    try {
      const res = await api.patch<{ status: string; data: SubscriptionResponse }>(`/v1/recurring/subscriptions/${id}`, payload);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          subscriptions: state.subscriptions.map((s) => (s.id === id ? updated : s)),
          loading: false,
        }));
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to update subscription', loading: false });
      return false;
    }
  },

  cancelSubscription: async (id) => {
    try {
      const res = await api.post<{ status: string; data: SubscriptionResponse }>(`/v1/recurring/subscriptions/${id}/cancel`);
      const updated = res.data?.data;
      if (updated) {
        set((state) => ({
          subscriptions: state.subscriptions.map((s) => (s.id === id ? updated : s)),
        }));
        return true;
      }
      return false;
    } catch (err: any) {
      set({ error: err.response?.data?.error?.message || 'Failed to cancel subscription' });
      return false;
    }
  },
}));
