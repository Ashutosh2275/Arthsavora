import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  TransactionResponse,
  TransactionCreateRequest,
  TransactionUpdateRequest,
  TransactionPostRequest,
  TransactionCancelRequest,
  TransactionReverseRequest,
  TransactionRefundRequest,
  TransferCreateRequest,
  TransferResponse,
  TransactionHistoryEntry,
  PaginatedResponse,
} from '@arthsavora/contracts';

interface TransactionFilters {
  page?: number;
  pageSize?: number;
  accountId?: string;
  categoryId?: string;
  status?: string;
  transactionType?: string;
  direction?: string;
  startDate?: string;
  endDate?: string;
  search?: string;
}

interface TransactionState {
  transactions: TransactionResponse[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  historyLoading: boolean;
  activeHistory: TransactionHistoryEntry[];
  selectedTransaction: TransactionResponse | null;

  fetchTransactions: (filters?: TransactionFilters) => Promise<void>;
  setSelectedTransaction: (tx: TransactionResponse | null) => void;
  createTransaction: (data: TransactionCreateRequest) => Promise<{ success: boolean; data?: TransactionResponse; error?: string }>;
  updateTransaction: (id: string, data: TransactionUpdateRequest) => Promise<{ success: boolean; data?: TransactionResponse; error?: string }>;
  postTransaction: (id: string, req?: TransactionPostRequest) => Promise<{ success: boolean; error?: string }>;
  cancelTransaction: (id: string, req?: TransactionCancelRequest) => Promise<{ success: boolean; error?: string }>;
  reverseTransaction: (id: string, req: TransactionReverseRequest) => Promise<{ success: boolean; data?: TransactionResponse; error?: string }>;
  refundTransaction: (id: string, req: TransactionRefundRequest) => Promise<{ success: boolean; data?: TransactionResponse; error?: string }>;
  createTransfer: (data: TransferCreateRequest) => Promise<{ success: boolean; data?: TransferResponse; error?: string }>;
  fetchHistory: (id: string) => Promise<void>;
}

export const useTransactionStore = create<TransactionState>((set, get) => ({
  transactions: [],
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
  historyLoading: false,
  activeHistory: [],
  selectedTransaction: null,

  fetchTransactions: async (filters = {}) => {
    set({ loading: true });
    try {
      const params = new URLSearchParams();
      params.append('page', String(filters.page || get().page));
      params.append('page_size', String(filters.pageSize || get().pageSize));
      if (filters.accountId) params.append('account_id', filters.accountId);
      if (filters.categoryId) params.append('category_id', filters.categoryId);
      if (filters.status && filters.status !== 'all') params.append('status', filters.status);
      if (filters.transactionType && filters.transactionType !== 'all') params.append('transaction_type', filters.transactionType);
      if (filters.direction && filters.direction !== 'all') params.append('direction', filters.direction);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.search) params.append('search', filters.search);

      const response = await api.get<PaginatedResponse<TransactionResponse>>(`/v1/transactions/?${params.toString()}`);
      set({
        transactions: response.data.items,
        total: response.data.total,
        page: response.data.page,
        pageSize: response.data.limit || 20,
        loading: false,
      });
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
      set({ loading: false });
    }
  },

  setSelectedTransaction: (tx) => {
    set({ selectedTransaction: tx });
  },

  createTransaction: async (data: TransactionCreateRequest) => {
    try {
      const response = await api.post<TransactionResponse>('/v1/transactions/', data);
      await get().fetchTransactions();
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to record transaction';
      return { success: false, error: message };
    }
  },

  updateTransaction: async (id: string, data: TransactionUpdateRequest) => {
    try {
      const response = await api.patch<TransactionResponse>(`/v1/transactions/${id}`, data);
      set({
        transactions: get().transactions.map((t) => (t.id === id ? response.data : t)),
      });
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to update transaction';
      return { success: false, error: message };
    }
  },

  postTransaction: async (id: string, req?: TransactionPostRequest) => {
    try {
      await api.post<TransactionResponse>(`/v1/transactions/${id}/post`, req || {});
      await get().fetchTransactions();
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to post transaction';
      return { success: false, error: message };
    }
  },

  cancelTransaction: async (id: string, req?: TransactionCancelRequest) => {
    try {
      await api.post<TransactionResponse>(`/v1/transactions/${id}/cancel`, req || {});
      await get().fetchTransactions();
      return { success: true };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to cancel transaction';
      return { success: false, error: message };
    }
  },

  reverseTransaction: async (id: string, req: TransactionReverseRequest) => {
    try {
      const response = await api.post<TransactionResponse>(`/v1/transactions/${id}/reverse`, req);
      await get().fetchTransactions();
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to reverse transaction';
      return { success: false, error: message };
    }
  },

  refundTransaction: async (id: string, req: TransactionRefundRequest) => {
    try {
      const response = await api.post<TransactionResponse>(`/v1/transactions/${id}/refunds`, req);
      await get().fetchTransactions();
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to refund transaction';
      return { success: false, error: message };
    }
  },

  createTransfer: async (data: TransferCreateRequest) => {
    try {
      const response = await api.post<TransferResponse>('/v1/transfers/', data);
      await get().fetchTransactions();
      return { success: true, data: response.data };
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message = axiosError.response?.data?.error?.message || 'Failed to execute transfer';
      return { success: false, error: message };
    }
  },

  fetchHistory: async (id: string) => {
    set({ historyLoading: true, activeHistory: [] });
    try {
      const response = await api.get<TransactionHistoryEntry[]>(`/v1/transactions/${id}/history`);
      set({ activeHistory: response.data, historyLoading: false });
    } catch (error) {
      console.error('Failed to fetch transaction history:', error);
      set({ historyLoading: false });
    }
  },
}));

export default useTransactionStore;
