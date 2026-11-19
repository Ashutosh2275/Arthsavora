import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  AccountingBasis,
  BalanceSheetDTO,
  CashFlowStatementDTO,
  CreateTaxEstimatePayload,
  GeneratedReportDTO,
  GenerateReportPayload,
  GSTReportSummaryDTO,
  IncomeExpenseStatementDTO,
  ReportingPeriodDTO,
  ReportValidationFindingDTO,
  ReviewTaxClassificationPayload,
  TaxClassificationDTO,
  TaxEstimateDTO,
  TrialBalanceDTO,
} from '@arthsavora/contracts';

interface FinancialReportState {
  periods: ReportingPeriodDTO[];
  selectedPeriod: ReportingPeriodDTO | null;
  accountingBasis: AccountingBasis;
  incomeStatement: IncomeExpenseStatementDTO | null;
  cashFlowStatement: CashFlowStatementDTO | null;
  balanceSheet: BalanceSheetDTO | null;
  trialBalance: TrialBalanceDTO | null;
  generatedReports: GeneratedReportDTO[];
  taxClassifications: TaxClassificationDTO[];
  gstSummary: GSTReportSummaryDTO | null;
  taxEstimate: TaxEstimateDTO | null;
  validationFindings: ReportValidationFindingDTO[];
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  setSelectedPeriod: (period: ReportingPeriodDTO | null) => void;
  setAccountingBasis: (basis: AccountingBasis) => void;
  fetchPeriods: () => Promise<void>;
  fetchIncomeStatement: (
    periodType?: string,
    fiscalYear?: string,
    quarter?: number,
    basis?: AccountingBasis
  ) => Promise<void>;
  fetchCashFlowStatement: (
    periodType?: string,
    fiscalYear?: string,
    quarter?: number
  ) => Promise<void>;
  fetchBalanceSheet: (asOfDate?: string) => Promise<void>;
  fetchTrialBalance: (asOfDate?: string) => Promise<void>;
  generateReportSnapshot: (payload: GenerateReportPayload) => Promise<GeneratedReportDTO>;
  fetchReportHistory: (reportType?: string) => Promise<void>;
  downloadReportCSV: (reportId: string, filename?: string) => Promise<void>;
  fetchValidations: (fiscalYear?: string) => Promise<void>;
  resolveValidation: (findingId: string, notes?: string) => Promise<void>;
  fetchTaxClassifications: (
    taxYear?: string,
    taxCategory?: string,
    reviewStatus?: string
  ) => Promise<void>;
  suggestTaxClassifications: (taxYear?: string) => Promise<void>;
  reviewTaxClassification: (
    transactionId: string,
    payload: ReviewTaxClassificationPayload
  ) => Promise<void>;
  fetchGSTSummary: (
    periodType?: string,
    fiscalYear?: string,
    quarter?: number
  ) => Promise<void>;
  fetchTaxEstimate: (financialYear?: string) => Promise<void>;
  createTaxEstimate: (payload: CreateTaxEstimatePayload) => Promise<TaxEstimateDTO>;
}

export const useFinancialReportStore = create<FinancialReportState>((set, get) => ({
  periods: [],
  selectedPeriod: null,
  accountingBasis: 'cash',
  incomeStatement: null,
  cashFlowStatement: null,
  balanceSheet: null,
  trialBalance: null,
  generatedReports: [],
  taxClassifications: [],
  gstSummary: null,
  taxEstimate: null,
  validationFindings: [],
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),
  setSelectedPeriod: (period) => set({ selectedPeriod: period }),
  setAccountingBasis: (basis) => set({ accountingBasis: basis }),

  fetchPeriods: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.get<ReportingPeriodDTO[]>('/reports/periods');
      const periods = response.data;
      set({
        periods,
        selectedPeriod: periods.length > 0 ? periods[0] : null,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch reporting periods',
        isLoading: false,
      });
    }
  },

  fetchIncomeStatement: async (periodType, fiscalYear, quarter, basis) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const effectiveBasis = basis || get().accountingBasis;
      const params: Record<string, any> = {
        period_type: periodType || currentPeriod?.period_type || 'financial_year',
        basis: effectiveBasis,
      };
      if (fiscalYear || currentPeriod?.fiscal_year) {
        params.fiscal_year = fiscalYear || currentPeriod?.fiscal_year;
      }
      if (quarter !== undefined || currentPeriod?.quarter) {
        params.quarter = quarter !== undefined ? quarter : currentPeriod?.quarter;
      }

      const response = await axios.get<IncomeExpenseStatementDTO>('/reports/income-statement', { params });
      set({ incomeStatement: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch income statement',
        isLoading: false,
      });
    }
  },

  fetchCashFlowStatement: async (periodType, fiscalYear, quarter) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const params: Record<string, any> = {
        period_type: periodType || currentPeriod?.period_type || 'financial_year',
      };
      if (fiscalYear || currentPeriod?.fiscal_year) {
        params.fiscal_year = fiscalYear || currentPeriod?.fiscal_year;
      }
      if (quarter !== undefined || currentPeriod?.quarter) {
        params.quarter = quarter !== undefined ? quarter : currentPeriod?.quarter;
      }

      const response = await axios.get<CashFlowStatementDTO>('/reports/cash-flow', { params });
      set({ cashFlowStatement: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch cash flow statement',
        isLoading: false,
      });
    }
  },

  fetchBalanceSheet: async (asOfDate) => {
    set({ isLoading: true, error: null });
    try {
      const params: Record<string, any> = {};
      if (asOfDate) params.as_of_date = asOfDate;
      const response = await axios.get<BalanceSheetDTO>('/reports/balance-sheet', { params });
      set({ balanceSheet: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch balance sheet',
        isLoading: false,
      });
    }
  },

  fetchTrialBalance: async (asOfDate) => {
    set({ isLoading: true, error: null });
    try {
      const params: Record<string, any> = {};
      if (asOfDate) params.as_of_date = asOfDate;
      const response = await axios.get<TrialBalanceDTO>('/reports/trial-balance', { params });
      set({ trialBalance: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch trial balance',
        isLoading: false,
      });
    }
  },

  generateReportSnapshot: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<GeneratedReportDTO>('/reports/generate', payload);
      set((state) => ({
        generatedReports: [response.data, ...state.generatedReports],
        isLoading: false,
      }));
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to generate report snapshot';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  fetchReportHistory: async (reportType) => {
    set({ isLoading: true, error: null });
    try {
      const params: Record<string, any> = { limit: 50 };
      if (reportType) params.report_type = reportType;
      const response = await axios.get<GeneratedReportDTO[]>('/reports/history', { params });
      set({ generatedReports: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch report history',
        isLoading: false,
      });
    }
  },

  downloadReportCSV: async (reportId, filename) => {
    try {
      const response = await axios.get(`/reports/${reportId}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || `report_${reportId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to download report CSV',
      });
    }
  },

  fetchValidations: async (fiscalYear) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const params: Record<string, any> = {};
      if (fiscalYear || currentPeriod?.fiscal_year) {
        params.fiscal_year = fiscalYear || currentPeriod?.fiscal_year;
      }
      const response = await axios.get<ReportValidationFindingDTO[]>('/reports/validation', { params });
      set({ validationFindings: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch validations',
        isLoading: false,
      });
    }
  },

  resolveValidation: async (findingId, notes) => {
    try {
      const response = await axios.post<ReportValidationFindingDTO>(
        `/reports/validation/${findingId}/resolve`,
        { notes }
      );
      set((state) => ({
        validationFindings: state.validationFindings.map((f) =>
          f.id === findingId ? response.data : f
        ),
      }));
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to resolve validation finding',
      });
    }
  },

  fetchTaxClassifications: async (taxYear, taxCategory, reviewStatus) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const params: Record<string, any> = { limit: 100 };
      if (taxYear || currentPeriod?.fiscal_year) {
        params.tax_year = taxYear || currentPeriod?.fiscal_year;
      }
      if (taxCategory) params.tax_category = taxCategory;
      if (reviewStatus) params.review_status = reviewStatus;

      const response = await axios.get<TaxClassificationDTO[]>('/tax/classifications', { params });
      set({ taxClassifications: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch tax classifications',
        isLoading: false,
      });
    }
  },

  suggestTaxClassifications: async (taxYear) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const payload = { tax_year: taxYear || currentPeriod?.fiscal_year };
      const response = await axios.post<TaxClassificationDTO[]>('/tax/classifications/suggest', payload);
      set((state) => ({
        taxClassifications: [...response.data, ...state.taxClassifications],
        isLoading: false,
      }));
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to generate tax suggestions',
        isLoading: false,
      });
    }
  },

  reviewTaxClassification: async (transactionId, payload) => {
    try {
      const response = await axios.post<TaxClassificationDTO>(
        `/tax/classifications/${transactionId}/review`,
        payload
      );
      set((state) => ({
        taxClassifications: state.taxClassifications.map((c) =>
          c.transaction_id === transactionId ? response.data : c
        ),
      }));
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to update tax classification',
      });
    }
  },

  fetchGSTSummary: async (periodType, fiscalYear, quarter) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const params: Record<string, any> = {
        period_type: periodType || currentPeriod?.period_type || 'financial_year',
      };
      if (fiscalYear || currentPeriod?.fiscal_year) {
        params.fiscal_year = fiscalYear || currentPeriod?.fiscal_year;
      }
      if (quarter !== undefined || currentPeriod?.quarter) {
        params.quarter = quarter !== undefined ? quarter : currentPeriod?.quarter;
      }

      const response = await axios.get<GSTReportSummaryDTO>('/tax/gst-summary', { params });
      set({ gstSummary: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch GST summary',
        isLoading: false,
      });
    }
  },

  fetchTaxEstimate: async (financialYear) => {
    set({ isLoading: true, error: null });
    try {
      const currentPeriod = get().selectedPeriod;
      const params: Record<string, any> = {};
      if (financialYear || currentPeriod?.fiscal_year) {
        params.financial_year = financialYear || currentPeriod?.fiscal_year;
      }
      const response = await axios.get<TaxEstimateDTO | null>('/tax/estimates', { params });
      set({ taxEstimate: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch tax estimate',
        isLoading: false,
      });
    }
  },

  createTaxEstimate: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<TaxEstimateDTO>('/tax/estimates', payload);
      set({ taxEstimate: response.data, isLoading: false });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to calculate tax estimate';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },
}));
