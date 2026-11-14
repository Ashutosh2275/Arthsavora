import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  AccountResponse,
  AccountCreateRequest,
  AccountBalanceSnapshotResponse,
  AccountBalanceSnapshotCreateRequest,
} from '@arthsavora/contracts';

interface AccountState {
  accounts: AccountResponse[];
  selectedAccount: AccountResponse | null;
  balanceHistory: AccountBalanceSnapshotResponse[];
  loading: boolean;
  historyLoading: boolean;

  fetchAccounts: () => Promise<void>;
  setSelectedAccount: (account: AccountResponse | null) => void;
  createAccount: (data: AccountCreateRequest) => Promise<{ success: boolean; data?: AccountResponse; error?: string }>;
  archiveAccount: (id: string) => Promise<{ success: boolean; error?: string }>;
  restoreAccount: (id: string) => Promise<{ success: boolean; error?: string }>;
  closeAccount: (id: string, closingDate: string) => Promise<{ success: boolean; error?: string }>;
  fetchBalanceHistory: (id: string) => Promise<void>;
  recordSnapshot: (id: string, payload: AccountBalanceSnapshotCreateRequest) => Promise<{ success: boolean; error?: string }>;
}

export const useAccountStore = create<AccountState>((set, get) => ({
  accounts: [],
  selectedAccount: null,
  balanceHistory: [],
  loading: false,
  historyLoading: false,

  fetchAccounts: async () => {
    set({ loading: true });
    try {
      const response = await api.get<AccountResponse[]>('/v1/accounts/');
      set({ accounts: response.data, loading: false });
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
      set({ loading: false });
    }
  },

  setSelectedAccount: (account) => {
    set({ selectedAccount: account });
  },

  createAccount: async (data: AccountCreateRequest) => {
    try {
      const response = await api.post<AccountResponse>('/v1/accounts/', data);
      set({ accounts: [response.data, ...get().accounts] });
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to create account';
      return { success: false, error: message };
    }
  },

  archiveAccount: async (id: string) => {
    try {
      const response = await api.post<AccountResponse>(`/v1/accounts/${id}/archive`);
      set({
        accounts: get().accounts.map((acc) => (acc.id === id ? response.data : acc)),
        selectedAccount: get().selectedAccount?.id === id ? response.data : get().selectedAccount,
      });
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      return { success: false, error: axiosError.response?.data?.error?.message || 'Failed to archive account' };
    }
  },

  restoreAccount: async (id: string) => {
    try {
      const response = await api.post<AccountResponse>(`/v1/accounts/${id}/restore`);
      set({
        accounts: get().accounts.map((acc) => (acc.id === id ? response.data : acc)),
        selectedAccount: get().selectedAccount?.id === id ? response.data : get().selectedAccount,
      });
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      return { success: false, error: axiosError.response?.data?.error?.message || 'Failed to restore account' };
    }
  },

  closeAccount: async (id: string, closingDate: string) => {
    try {
      const response = await api.post<AccountResponse>(`/v1/accounts/${id}/close`, { closing_date: closingDate });
      set({
        accounts: get().accounts.map((acc) => (acc.id === id ? response.data : acc)),
        selectedAccount: get().selectedAccount?.id === id ? response.data : get().selectedAccount,
      });
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      return { success: false, error: axiosError.response?.data?.error?.message || 'Failed to close account' };
    }
  },

  fetchBalanceHistory: async (id: string) => {
    set({ historyLoading: true });
    try {
      const response = await api.get<AccountBalanceSnapshotResponse[]>(`/v1/accounts/${id}/balance-history`);
      set({ balanceHistory: response.data, historyLoading: false });
    } catch (error) {
      console.error('Failed to fetch balance history:', error);
      set({ historyLoading: false });
    }
  },

  recordSnapshot: async (id: string, payload: AccountBalanceSnapshotCreateRequest) => {
    try {
      const response = await api.post<AccountBalanceSnapshotResponse>(`/v1/accounts/${id}/balances/snapshot`, payload);
      set({ balanceHistory: [response.data, ...get().balanceHistory] });
      // Refresh accounts to reflect updated fast pointer
      await get().fetchAccounts();
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      return { success: false, error: axiosError.response?.data?.error?.message || 'Failed to record snapshot' };
    }
  },
}));

export default useAccountStore;
