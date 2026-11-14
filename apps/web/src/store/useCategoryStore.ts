import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  CategoryResponse,
  CategoryTreeResponse,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  RuleResponse,
  RuleCreateRequest,
  MerchantResponse,
  ClassificationResponse,
  FeedbackSubmitRequest,
  FeedbackResponse,
  PreviewSuggestResponse,
} from '@arthsavora/contracts';

interface CategoryState {
  categories: CategoryResponse[];
  categoryTree: CategoryTreeResponse[];
  rules: RuleResponse[];
  merchants: MerchantResponse[];
  activeClassification: ClassificationResponse | null;
  loading: boolean;
  error: string | null;

  fetchCategories: (type?: string) => Promise<void>;
  fetchCategoryTree: (type?: string) => Promise<void>;
  createCategory: (payload: CategoryCreateRequest) => Promise<CategoryResponse>;
  updateCategory: (id: string, payload: CategoryUpdateRequest) => Promise<CategoryResponse>;
  deleteCategory: (id: string, reassignToId?: string) => Promise<void>;

  fetchRules: () => Promise<void>;
  createRule: (payload: RuleCreateRequest) => Promise<RuleResponse>;
  deleteRule: (id: string) => Promise<void>;

  fetchMerchants: (search?: string) => Promise<void>;

  categorizeTransaction: (txId: string, force?: boolean) => Promise<ClassificationResponse>;
  fetchClassification: (txId: string) => Promise<ClassificationResponse | null>;
  submitFeedback: (txId: string, payload: FeedbackSubmitRequest) => Promise<FeedbackResponse>;
  previewSuggestion: (description: string, direction?: string) => Promise<PreviewSuggestResponse>;
}

export const useCategoryStore = create<CategoryState>((set, get) => ({
  categories: [],
  categoryTree: [],
  rules: [],
  merchants: [],
  activeClassification: null,
  loading: false,
  error: null,

  fetchCategories: async (type?: string) => {
    set({ loading: true, error: null });
    try {
      const params = type ? { category_type: type } : {};
      const res = await api.get('/categories', { params });
      set({ categories: res.data.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to fetch categories', loading: false });
    }
  },

  fetchCategoryTree: async (type?: string) => {
    set({ loading: true, error: null });
    try {
      const params = type ? { category_type: type } : {};
      const res = await api.get('/categories/tree', { params });
      set({ categoryTree: res.data.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to fetch category tree', loading: false });
    }
  },

  createCategory: async (payload: CategoryCreateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post('/categories', payload);
      const created = res.data.data;
      set((state) => ({ categories: [...state.categories, created], loading: false }));
      return created;
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to create category', loading: false });
      throw err;
    }
  },

  updateCategory: async (id: string, payload: CategoryUpdateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.patch(`/categories/${id}`, payload);
      const updated = res.data.data;
      set((state) => ({
        categories: state.categories.map((c) => (c.id === id ? updated : c)),
        loading: false,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to update category', loading: false });
      throw err;
    }
  },

  deleteCategory: async (id: string, reassignToId?: string) => {
    set({ loading: true, error: null });
    try {
      const params = reassignToId ? { reassign_to_id: reassignToId } : {};
      await api.delete(`/categories/${id}`, { params });
      set((state) => ({
        categories: state.categories.filter((c) => c.id !== id),
        loading: false,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to delete category', loading: false });
      throw err;
    }
  },

  fetchRules: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.get('/rules');
      set({ rules: res.data.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to fetch rules', loading: false });
    }
  },

  createRule: async (payload: RuleCreateRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post('/rules', payload);
      const created = res.data.data;
      set((state) => ({ rules: [created, ...state.rules], loading: false }));
      return created;
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to create rule', loading: false });
      throw err;
    }
  },

  deleteRule: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await api.delete(`/rules/${id}`);
      set((state) => ({
        rules: state.rules.filter((r) => r.id !== id),
        loading: false,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to delete rule', loading: false });
      throw err;
    }
  },

  fetchMerchants: async (search?: string) => {
    set({ loading: true, error: null });
    try {
      const params = search ? { search } : {};
      const res = await api.get('/merchants', { params });
      set({ merchants: res.data.data, loading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to fetch merchants', loading: false });
    }
  },

  categorizeTransaction: async (txId: string, force: boolean = false) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post(`/transactions/${txId}/categorize`, null, {
        params: { force_reclassify: force },
      });
      const classification = res.data.data;
      set({ activeClassification: classification, loading: false });
      return classification;
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to categorize transaction', loading: false });
      throw err;
    }
  },

  fetchClassification: async (txId: string) => {
    try {
      const res = await api.get(`/transactions/${txId}/classification`);
      const classification = res.data.data;
      if (classification) {
        set({ activeClassification: classification });
      }
      return classification;
    } catch {
      return null;
    }
  },

  submitFeedback: async (txId: string, payload: FeedbackSubmitRequest) => {
    set({ loading: true, error: null });
    try {
      const res = await api.post(`/transactions/${txId}/feedback`, payload);
      set({ loading: false });
      return res.data.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || 'Failed to submit feedback', loading: false });
      throw err;
    }
  },

  previewSuggestion: async (description: string, direction: string = 'outflow') => {
    try {
      const res = await api.post('/categories/suggest', { description, direction });
      return res.data.data;
    } catch (err: any) {
      throw err;
    }
  },
}));

export default useCategoryStore;
