import { create } from 'zustand';
import type {
  AnomalyDetectionResponse,
  AnomalyReviewRequest,
  AnomalyScanRequest,
  AnomalySummaryResponse,
  AnomalyTrendPoint,
  DetectionExceptionCreateRequest,
  DetectionExceptionResponse,
  DetectionRuleResponse,
  DetectionRuleUpdateRequest,
} from '@arthsavora/contracts';
import api from '@/lib/axios';

interface AnomalyState {
  anomalies: AnomalyDetectionResponse[];
  selectedAnomaly: AnomalyDetectionResponse | null;
  summary: AnomalySummaryResponse | null;
  trends: AnomalyTrendPoint[];
  rules: DetectionRuleResponse[];
  exceptions: DetectionExceptionResponse[];
  statusFilter: string | null;
  severityFilter: string | null;
  isLoading: boolean;
  error: string | null;

  setStatusFilter: (status: string | null) => void;
  setSeverityFilter: (severity: string | null) => void;
  fetchAnomalies: (status?: string | null, severity?: string | null) => Promise<void>;
  fetchAnomalyDetails: (id: string) => Promise<AnomalyDetectionResponse>;
  fetchSummary: () => Promise<void>;
  fetchTrends: (lookbackDays?: number) => Promise<void>;
  scanRecentTransactions: (lookbackDays?: number, forceRecheck?: boolean) => Promise<void>;
  reviewAnomaly: (id: string, req: AnomalyReviewRequest) => Promise<void>;
  acknowledgeAnomaly: (id: string) => Promise<void>;
  dismissAnomaly: (id: string, reason?: string) => Promise<void>;
  fetchRules: () => Promise<void>;
  updateRule: (id: string, req: DetectionRuleUpdateRequest) => Promise<void>;
  fetchExceptions: () => Promise<void>;
  createException: (req: DetectionExceptionCreateRequest) => Promise<void>;
  deleteException: (id: string) => Promise<void>;
}

export const useAnomalyStore = create<AnomalyState>((set, get) => ({
  anomalies: [],
  selectedAnomaly: null,
  summary: null,
  trends: [],
  rules: [],
  exceptions: [],
  statusFilter: null,
  severityFilter: null,
  isLoading: false,
  error: null,

  setStatusFilter: (status: string | null) => {
    set({ statusFilter: status });
    get().fetchAnomalies(status, get().severityFilter);
  },

  setSeverityFilter: (severity: string | null) => {
    set({ severityFilter: severity });
    get().fetchAnomalies(get().statusFilter, severity);
  },

  fetchAnomalies: async (statusFilter?: string | null, severityFilter?: string | null) => {
    const s = statusFilter !== undefined ? statusFilter : get().statusFilter;
    const sev = severityFilter !== undefined ? severityFilter : get().severityFilter;
    set({ isLoading: true, error: null });
    try {
      const params: Record<string, string> = {};
      if (s) params.status = s;
      if (sev) params.severity = sev;

      const res = await api.get('/v1/anomalies', { params });
      set({ anomalies: res.data.data, isLoading: false });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to fetch anomaly detections.',
      });
    }
  },

  fetchAnomalyDetails: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.get(`/v1/anomalies/${id}`);
      const anomaly = res.data.data;
      set({ selectedAnomaly: anomaly, isLoading: false });
      return anomaly;
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to fetch anomaly details.',
      });
      throw err;
    }
  },

  fetchSummary: async () => {
    try {
      const res = await api.get('/v1/anomalies/summary');
      set({ summary: res.data.data });
    } catch (err: any) {
      console.error('Failed to fetch anomaly summary:', err);
    }
  },

  fetchTrends: async (lookbackDays = 30) => {
    try {
      const res = await api.get('/v1/anomalies/trends', { params: { lookback_days: lookbackDays } });
      set({ trends: res.data.data.trends || [] });
    } catch (err: any) {
      console.error('Failed to fetch anomaly trends:', err);
    }
  },

  scanRecentTransactions: async (lookbackDays = 7, forceRecheck = false) => {
    set({ isLoading: true, error: null });
    try {
      const payload: AnomalyScanRequest = {
        lookback_days: lookbackDays,
        force_recheck: forceRecheck,
      };
      await api.post('/v1/anomalies/scan', payload);
      await Promise.all([
        get().fetchAnomalies(),
        get().fetchSummary(),
        get().fetchTrends(),
      ]);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to scan recent transactions.',
      });
    }
  },

  reviewAnomaly: async (id: string, req: AnomalyReviewRequest) => {
    try {
      const res = await api.post(`/v1/anomalies/${id}/review`, req);
      const updated = res.data.data;
      set((state) => ({
        anomalies: state.anomalies.map((a) => (a.id === id ? updated : a)),
        selectedAnomaly: state.selectedAnomaly?.id === id ? updated : state.selectedAnomaly,
      }));
      get().fetchSummary();
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to submit review.' });
      throw err;
    }
  },

  acknowledgeAnomaly: async (id: string) => {
    try {
      const res = await api.post(`/v1/anomalies/${id}/acknowledge`);
      const updated = res.data.data;
      set((state) => ({
        anomalies: state.anomalies.map((a) => (a.id === id ? updated : a)),
        selectedAnomaly: state.selectedAnomaly?.id === id ? updated : state.selectedAnomaly,
      }));
      get().fetchSummary();
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to acknowledge anomaly.' });
      throw err;
    }
  },

  dismissAnomaly: async (id: string, reason?: string) => {
    try {
      const res = await api.post(`/v1/anomalies/${id}/dismiss`, null, { params: { reason } });
      const updated = res.data.data;
      set((state) => ({
        anomalies: state.anomalies.map((a) => (a.id === id ? updated : a)),
        selectedAnomaly: state.selectedAnomaly?.id === id ? updated : state.selectedAnomaly,
      }));
      get().fetchSummary();
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to dismiss anomaly.' });
      throw err;
    }
  },

  fetchRules: async () => {
    try {
      const res = await api.get('/v1/anomalies/rules/list');
      set({ rules: res.data.data });
    } catch (err: any) {
      console.error('Failed to fetch detection rules:', err);
    }
  },

  updateRule: async (id: string, req: DetectionRuleUpdateRequest) => {
    try {
      const res = await api.patch(`/v1/anomalies/rules/${id}`, req);
      const updated = res.data.data;
      set((state) => ({
        rules: state.rules.map((r) => (r.id === id ? updated : r)),
      }));
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to update rule.' });
      throw err;
    }
  },

  fetchExceptions: async () => {
    try {
      const res = await api.get('/v1/anomalies/exceptions/list');
      set({ exceptions: res.data.data });
    } catch (err: any) {
      console.error('Failed to fetch detection exceptions:', err);
    }
  },

  createException: async (req: DetectionExceptionCreateRequest) => {
    try {
      const res = await api.post('/v1/anomalies/exceptions', req);
      set((state) => ({
        exceptions: [res.data.data, ...state.exceptions],
      }));
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to create exception.' });
      throw err;
    }
  },

  deleteException: async (id: string) => {
    try {
      await api.delete(`/v1/anomalies/exceptions/${id}`);
      set((state) => ({
        exceptions: state.exceptions.filter((e) => e.id !== id),
      }));
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to delete exception.' });
      throw err;
    }
  },
}));
