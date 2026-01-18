import { create } from 'zustand';
import api from '../api/axios';

const useExpenseStore = create((set, get) => ({
  expenses: [],
  loading: false,

  fetchExpenses: async () => {
    set({ loading: true });
    try {
      const response = await api.get('/expenses/');
      set({ expenses: response.data, loading: false });
    } catch (error) {
      console.error("Fetch Error:", error);
      set({ loading: false });
    }
  },

  addExpense: async (expenseData) => {
    try {
      const response = await api.post('/expenses/', expenseData);
      set({ expenses: [response.data, ...get().expenses] });
      return { success: true };
    } catch (error) {
      console.error("Add Error:", error);
      return { success: false };
    }
  },
    parseSMS: async (smsText) => {
    try {
      // Ensure the URL is exactly /ml/parse-sms (backend prefix /api is added by axios.js)
      const response = await api.post('/ml/parse-sms', { text: smsText });
      return { success: true, data: response.data };
    } catch (error) {
      console.error("AI Parse Error:", error);
      return { success: false, error: "Failed to parse SMS" };
    }
  },
  deleteExpense: async (id) => {
    try {
      await api.delete(`/expenses/${id}`);
      set({ expenses: get().expenses.filter(e => e._id !== id) });
    } catch (error) {
      console.error("Delete failed:", error);
    }
  }
}));

export default useExpenseStore;