import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  CashFlowTrendsResponse,
  CategorySpendingResponse,
  FinancialOverviewResponse,
  MerchantSpendingResponse,
  NetWorthResponse,
  PeriodComparisonResponse,
  PeriodGrouping,
  ReportType,
} from '@arthsavora/contracts';

export type DatePreset =
  | 'this_month'
  | 'last_month'
  | 'this_quarter'
  | 'current_fy'
  | 'last_30_days'
  | 'last_90_days'
  | 'custom';

interface AnalyticsFilters {
  datePreset: DatePreset;
  startDate: string;
  endDate: string;
  grouping: PeriodGrouping;
  currency: string;
  selectedAccountId: string | null;
}

interface AnalyticsState extends AnalyticsFilters {
  overview: FinancialOverviewResponse | null;
  cashFlow: CashFlowTrendsResponse | null;
  categorySpending: CategorySpendingResponse | null;
  merchantSpending: MerchantSpendingResponse | null;
  netWorth: NetWorthResponse | null;
  comparison: PeriodComparisonResponse | null;
  loading: boolean;
  error: string | null;

  // Filter setters
  setDatePreset: (preset: DatePreset) => void;
  setCustomDateRange: (start: string, end: string) => void;
  setGrouping: (grouping: PeriodGrouping) => void;
  setCurrency: (currency: string) => void;
  setSelectedAccountId: (accountId: string | null) => void;

  // Data fetchers
  fetchAnalytics: () => Promise<void>;
  exportCSV: (reportType: ReportType) => Promise<Blob | null>;
}

function computePresetDates(preset: DatePreset): { startDate: string; endDate: string } {
  const now = new Date();
  const todayStr = now.toISOString().split('T')[0];

  if (preset === 'this_month') {
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    return { startDate: start.toISOString().split('T')[0], endDate: todayStr };
  }

  if (preset === 'last_month') {
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const end = new Date(now.getFullYear(), now.getMonth(), 0);
    return { startDate: start.toISOString().split('T')[0], endDate: end.toISOString().split('T')[0] };
  }

  if (preset === 'this_quarter') {
    const q = Math.floor(now.getMonth() / 3);
    const start = new Date(now.getFullYear(), q * 3, 1);
    return { startDate: start.toISOString().split('T')[0], endDate: todayStr };
  }

  if (preset === 'current_fy') {
    const fyStartYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
    const start = new Date(fyStartYear, 3, 1); // 1st April
    return { startDate: start.toISOString().split('T')[0], endDate: todayStr };
  }

  if (preset === 'last_30_days') {
    const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    return { startDate: start.toISOString().split('T')[0], endDate: todayStr };
  }

  if (preset === 'last_90_days') {
    const start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    return { startDate: start.toISOString().split('T')[0], endDate: todayStr };
  }

  return { startDate: todayStr, endDate: todayStr };
}

const initialDates = computePresetDates('this_month');

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  datePreset: 'this_month',
  startDate: initialDates.startDate,
  endDate: initialDates.endDate,
  grouping: 'month',
  currency: 'INR',
  selectedAccountId: null,

  overview: null,
  cashFlow: null,
  categorySpending: null,
  merchantSpending: null,
  netWorth: null,
  comparison: null,
  loading: false,
  error: null,

  setDatePreset: (preset) => {
    if (preset === 'custom') {
      set({ datePreset: 'custom' });
    } else {
      const dates = computePresetDates(preset);
      set({ datePreset: preset, startDate: dates.startDate, endDate: dates.endDate });
      get().fetchAnalytics();
    }
  },

  setCustomDateRange: (start, end) => {
    set({ datePreset: 'custom', startDate: start, endDate: end });
    get().fetchAnalytics();
  },

  setGrouping: (grouping) => {
    set({ grouping });
    get().fetchAnalytics();
  },

  setCurrency: (currency) => {
    set({ currency });
    get().fetchAnalytics();
  },

  setSelectedAccountId: (accountId) => {
    set({ selectedAccountId: accountId });
    get().fetchAnalytics();
  },

  fetchAnalytics: async () => {
    const { startDate, endDate, grouping, currency, selectedAccountId } = get();
    set({ loading: true, error: null });

    const baseParams: Record<string, string> = {
      start_date: startDate,
      end_date: endDate,
      currency,
    };
    if (selectedAccountId) {
      baseParams.account_id = selectedAccountId;
    }

    try {
      const [ovRes, cfRes, catRes, mRes, nwRes, compRes] = await Promise.allSettled([
        api.get<{ success: boolean; data: FinancialOverviewResponse }>('/v1/analytics/overview', { params: baseParams }),
        api.get<{ success: boolean; data: CashFlowTrendsResponse }>('/v1/analytics/cash-flow', {
          params: { ...baseParams, grouping },
        }),
        api.get<{ success: boolean; data: CategorySpendingResponse }>('/v1/analytics/categories', {
          params: { ...baseParams, direction: 'outflow', limit: 10 },
        }),
        api.get<{ success: boolean; data: MerchantSpendingResponse }>('/v1/analytics/merchants', {
          params: { ...baseParams, limit: 10 },
        }),
        api.get<{ success: boolean; data: NetWorthResponse }>('/v1/analytics/net-worth', {
          params: { currency },
        }),
        api.get<{ success: boolean; data: PeriodComparisonResponse }>('/v1/analytics/comparison', {
          params: { current_start: startDate, current_end: endDate, currency },
        }),
      ]);

      set({
        overview: ovRes.status === 'fulfilled' ? ovRes.value.data.data : null,
        cashFlow: cfRes.status === 'fulfilled' ? cfRes.value.data.data : null,
        categorySpending: catRes.status === 'fulfilled' ? catRes.value.data.data : null,
        merchantSpending: mRes.status === 'fulfilled' ? mRes.value.data.data : null,
        netWorth: nwRes.status === 'fulfilled' ? nwRes.value.data.data : null,
        comparison: compRes.status === 'fulfilled' ? compRes.value.data.data : null,
        loading: false,
      });
    } catch (err: any) {
      console.error('Failed to load financial analytics:', err);
      set({ error: err?.message || 'Failed to fetch analytics', loading: false });
    }
  },

  exportCSV: async (reportType: ReportType) => {
    const { startDate, endDate, currency, selectedAccountId } = get();
    const params: Record<string, string> = {
      report_type: reportType,
      start_date: startDate,
      end_date: endDate,
      currency,
    };
    if (selectedAccountId) {
      params.account_id = selectedAccountId;
    }

    try {
      const response = await api.get('/v1/analytics/export', {
        params,
        responseType: 'blob',
      });
      return response.data;
    } catch (err) {
      console.error('Failed to export CSV report:', err);
      return null;
    }
  },
}));
