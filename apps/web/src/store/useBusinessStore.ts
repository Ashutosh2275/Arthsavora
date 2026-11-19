import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  BusinessActivityDTO,
  BusinessAnalyticsDTO,
  BusinessClientDTO,
  BusinessInvoiceDTO,
  BusinessOverviewDTO,
  BusinessPayableDTO,
  BusinessProfileDTO,
  BusinessVendorDTO,
  PayablesAgingDTO,
  ReceivablesAgingDTO,
} from '@arthsavora/contracts';

interface BusinessState {
  profile: BusinessProfileDTO | null;
  overview: BusinessOverviewDTO | null;
  clients: BusinessClientDTO[];
  totalClients: number;
  vendors: BusinessVendorDTO[];
  totalVendors: number;
  invoices: BusinessInvoiceDTO[];
  totalInvoices: number;
  currentInvoice: BusinessInvoiceDTO | null;
  payables: BusinessPayableDTO[];
  totalPayables: number;
  arAging: ReceivablesAgingDTO | null;
  apAging: PayablesAgingDTO | null;
  analytics: BusinessAnalyticsDTO | null;
  activities: BusinessActivityDTO[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchProfile: (workspaceId?: string) => Promise<void>;
  updateProfile: (data: Partial<BusinessProfileDTO>, workspaceId?: string) => Promise<void>;
  fetchOverview: (workspaceId?: string) => Promise<void>;
  fetchClients: (workspaceId?: string, search?: string, status?: string) => Promise<void>;
  createClient: (data: any, workspaceId?: string) => Promise<BusinessClientDTO>;
  updateClient: (clientId: string, data: any, workspaceId?: string) => Promise<void>;
  fetchVendors: (workspaceId?: string, search?: string, status?: string) => Promise<void>;
  createVendor: (data: any, workspaceId?: string) => Promise<BusinessVendorDTO>;
  updateVendor: (vendorId: string, data: any, workspaceId?: string) => Promise<void>;
  fetchInvoices: (workspaceId?: string, status?: string) => Promise<void>;
  fetchInvoice: (invoiceId: string, workspaceId?: string) => Promise<BusinessInvoiceDTO>;
  createInvoice: (data: any, workspaceId?: string) => Promise<BusinessInvoiceDTO>;
  issueInvoice: (invoiceId: string, workspaceId?: string) => Promise<void>;
  cancelInvoice: (invoiceId: string, reason: string, workspaceId?: string) => Promise<void>;
  recordInvoicePayment: (invoiceId: string, data: any, workspaceId?: string) => Promise<void>;
  fetchPayables: (workspaceId?: string, status?: string) => Promise<void>;
  createPayable: (data: any, workspaceId?: string) => Promise<BusinessPayableDTO>;
  recordPayablePayment: (payableId: string, data: any, workspaceId?: string) => Promise<void>;
  fetchReceivablesAging: (workspaceId?: string) => Promise<void>;
  fetchPayablesSummary: (workspaceId?: string) => Promise<void>;
  fetchAnalytics: (workspaceId?: string) => Promise<void>;
  fetchActivities: (workspaceId?: string) => Promise<void>;
  exportInvoicesCsv: (workspaceId?: string) => Promise<string>;
}

const getBaseUrl = (workspaceId?: string) => {
  return workspaceId ? `/workspaces/${workspaceId}/business` : '/business';
};

export const useBusinessStore = create<BusinessState>((set, get) => ({
  profile: null,
  overview: null,
  clients: [],
  totalClients: 0,
  vendors: [],
  totalVendors: 0,
  invoices: [],
  totalInvoices: 0,
  currentInvoice: null,
  payables: [],
  totalPayables: 0,
  arAging: null,
  apAging: null,
  analytics: null,
  activities: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchProfile: async (workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/profile`);
      set({ profile: res.data, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  updateProfile: async (data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.put(`${getBaseUrl(workspaceId)}/profile`, data);
      set({ profile: res.data, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  fetchOverview: async (workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/overview`);
      set({ overview: res.data, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  fetchClients: async (workspaceId, search, status) => {
    set({ isLoading: true, error: null });
    try {
      const params: any = {};
      if (search) params.search = search;
      if (status) params.status = status;
      const res = await axios.get(`${getBaseUrl(workspaceId)}/clients`, { params });
      set({ clients: res.data, totalClients: res.data.length, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  createClient: async (data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/clients`, data);
      set((state) => ({
        clients: [res.data, ...state.clients],
        totalClients: state.totalClients + 1,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  updateClient: async (clientId, data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.put(`${getBaseUrl(workspaceId)}/clients/${clientId}`, data);
      set((state) => ({
        clients: state.clients.map((c) => (c.id === clientId ? res.data : c)),
        isLoading: false,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  fetchVendors: async (workspaceId, search, status) => {
    set({ isLoading: true, error: null });
    try {
      const params: any = {};
      if (search) params.search = search;
      if (status) params.status = status;
      const res = await axios.get(`${getBaseUrl(workspaceId)}/vendors`, { params });
      set({ vendors: res.data, totalVendors: res.data.length, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  createVendor: async (data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/vendors`, data);
      set((state) => ({
        vendors: [res.data, ...state.vendors],
        totalVendors: state.totalVendors + 1,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  updateVendor: async (vendorId, data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.put(`${getBaseUrl(workspaceId)}/vendors/${vendorId}`, data);
      set((state) => ({
        vendors: state.vendors.map((v) => (v.id === vendorId ? res.data : v)),
        isLoading: false,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  fetchInvoices: async (workspaceId, status) => {
    set({ isLoading: true, error: null });
    try {
      const params: any = {};
      if (status) params.status = status;
      const res = await axios.get(`${getBaseUrl(workspaceId)}/invoices`, { params });
      set({ invoices: res.data, totalInvoices: res.data.length, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  fetchInvoice: async (invoiceId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/invoices/${invoiceId}`);
      set({ currentInvoice: res.data, isLoading: false });
      return res.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  createInvoice: async (data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/invoices`, data);
      set((state) => ({
        invoices: [res.data, ...state.invoices],
        totalInvoices: state.totalInvoices + 1,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  issueInvoice: async (invoiceId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/invoices/${invoiceId}/issue`);
      set((state) => ({
        invoices: state.invoices.map((inv) => (inv.id === invoiceId ? res.data : inv)),
        currentInvoice: res.data,
        isLoading: false,
      }));
      get().fetchOverview(workspaceId);
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  cancelInvoice: async (invoiceId, reason, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/invoices/${invoiceId}/cancel`, { reason });
      set((state) => ({
        invoices: state.invoices.map((inv) => (inv.id === invoiceId ? res.data : inv)),
        currentInvoice: res.data,
        isLoading: false,
      }));
      get().fetchOverview(workspaceId);
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  recordInvoicePayment: async (invoiceId, data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      await axios.post(`${getBaseUrl(workspaceId)}/invoices/${invoiceId}/payments`, data);
      await get().fetchInvoices(workspaceId);
      await get().fetchOverview(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  fetchPayables: async (workspaceId, status) => {
    set({ isLoading: true, error: null });
    try {
      const params: any = {};
      if (status) params.status = status;
      const res = await axios.get(`${getBaseUrl(workspaceId)}/payables`, { params });
      set({ payables: res.data, totalPayables: res.data.length, isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  createPayable: async (data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.post(`${getBaseUrl(workspaceId)}/payables`, data);
      set((state) => ({
        payables: [res.data, ...state.payables],
        totalPayables: state.totalPayables + 1,
        isLoading: false,
      }));
      get().fetchOverview(workspaceId);
      return res.data;
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  recordPayablePayment: async (payableId, data, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      await axios.post(`${getBaseUrl(workspaceId)}/payables/${payableId}/payments`, data);
      await get().fetchPayables(workspaceId);
      await get().fetchOverview(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
      throw err;
    }
  },

  fetchReceivablesAging: async (workspaceId) => {
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/receivables`);
      set({ arAging: res.data });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message });
    }
  },

  fetchPayablesSummary: async (workspaceId) => {
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/payables/summary`);
      set({ apAging: res.data });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message });
    }
  },

  fetchAnalytics: async (workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/analytics`);
      set({
        analytics: res.data,
        overview: res.data.kpis,
        arAging: res.data.ar_aging,
        apAging: res.data.ap_aging,
        isLoading: false,
      });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message, isLoading: false });
    }
  },

  fetchActivities: async (workspaceId) => {
    try {
      const res = await axios.get(`${getBaseUrl(workspaceId)}/activity`);
      set({ activities: res.data });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message });
    }
  },

  exportInvoicesCsv: async (workspaceId) => {
    const res = await axios.get(`${getBaseUrl(workspaceId)}/reports/export?format=csv`, {
      responseType: 'text',
    });
    return res.data;
  },
}));
