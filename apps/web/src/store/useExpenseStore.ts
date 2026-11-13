import { create } from 'zustand';
import api from '@/lib/axios';
import type { ExpenseResponse, ExpenseCreateRequest, SmsParseResponse } from '@arthsavora/contracts';

interface ExpenseState {
  expenses: ExpenseResponse[];
  loading: boolean;
  fetchExpenses: () => Promise<void>;
  addExpense: (expenseData: ExpenseCreateRequest) => Promise<{ success: boolean; data?: ExpenseResponse }>;
  parseSMS: (smsText: string) => Promise<{ success: boolean; data?: SmsParseResponse; error?: string }>;
  deleteExpense: (id: string) => Promise<boolean>;
}

export const useExpenseStore = create<ExpenseState>((set, get) => ({
  expenses: [],
  loading: false,

  fetchExpenses: async () => {
    set({ loading: true });
    try {
      const response = await api.get<ExpenseResponse[]>('/expenses/');
      set({ expenses: response.data, loading: false });
    } catch (error) {
      console.error('Fetch error:', error);
      set({ loading: false });
    }
  },

  addExpense: async (expenseData: ExpenseCreateRequest) => {
    try {
      const response = await api.post<ExpenseResponse>('/expenses/', expenseData);
      set({ expenses: [response.data, ...get().expenses] });
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Add error:', error);
      return { success: false };
    }
  },

  parseSMS: async (smsText: string) => {
    try {
      const response = await api.post<SmsParseResponse>('/ml/parse-sms', { text: smsText });
      return { success: true, data: response.data };
    } catch (error) {
      console.error('AI parse error:', error);
      return { success: false, error: 'Failed to parse SMS' };
    }
  },

  deleteExpense: async (id: string) => {
    try {
      await api.delete(`/expenses/${id}`);
      set({ expenses: get().expenses.filter((e) => (e.id || (e as { _id?: string })._id) !== id) });
      return true;
    } catch (error) {
      console.error('Delete failed:', error);
      return false;
    }
  },
}));

export default useExpenseStore;
