import { create } from 'zustand';
import axios from '../lib/axios';
import {
  AccountingPeriodResponse,
  JournalEntryCreateRequest,
  JournalEntryResponse,
  JournalListResponse,
  LedgerAccountCreateRequest,
  LedgerAccountResponse,
  TrialBalanceResponse,
} from '@arthsavora/contracts';

interface LedgerState {
  accounts: LedgerAccountResponse[];
  journals: JournalEntryResponse[];
  periods: AccountingPeriodResponse[];
  trialBalance: TrialBalanceResponse | null;
  selectedJournal: JournalEntryResponse | null;
  totalJournals: number;
  isLoading: boolean;
  error: string | null;

  fetchAccounts: (workspaceId?: string) => Promise<void>;
  fetchJournals: (workspaceId?: string, params?: Record<string, unknown>) => Promise<void>;
  fetchPeriods: (workspaceId?: string) => Promise<void>;
  fetchTrialBalance: (workspaceId?: string, asOfDate?: string) => Promise<void>;
  getJournal: (journalId: string, workspaceId?: string) => Promise<JournalEntryResponse>;
  createJournal: (payload: JournalEntryCreateRequest, workspaceId?: string) => Promise<JournalEntryResponse>;
  postJournal: (journalId: string, workspaceId?: string) => Promise<JournalEntryResponse>;
  reverseJournal: (journalId: string, reason: string, workspaceId?: string) => Promise<JournalEntryResponse>;
  createAccount: (payload: LedgerAccountCreateRequest, workspaceId?: string) => Promise<LedgerAccountResponse>;
  setSelectedJournal: (journal: JournalEntryResponse | null) => void;
  clearError: () => void;
}

export const useLedgerStore = create<LedgerState>((set, get) => ({
  accounts: [],
  journals: [],
  periods: [],
  trialBalance: null,
  selectedJournal: null,
  totalJournals: 0,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),
  setSelectedJournal: (journal) => set({ selectedJournal: journal }),

  fetchAccounts: async (workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/accounts`
        : '/api/v1/ledger/accounts';
      const res = await axios.get<LedgerAccountResponse[]>(url);
      set({ accounts: res.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail?.message || err.message || 'Failed to fetch chart of accounts',
        isLoading: false,
      });
    }
  },

  fetchJournals: async (workspaceId, params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/journals`
        : '/api/v1/ledger/journals';
      const res = await axios.get<JournalListResponse>(url, { params });
      set({
        journals: res.data.items,
        totalJournals: res.data.total,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail?.message || err.message || 'Failed to fetch journals',
        isLoading: false,
      });
    }
  },

  fetchPeriods: async (workspaceId) => {
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/periods`
        : '/api/v1/ledger/periods';
      const res = await axios.get<AccountingPeriodResponse[]>(url);
      set({ periods: res.data });
    } catch (err: any) {
      console.error('Failed to fetch accounting periods:', err);
    }
  },

  fetchTrialBalance: async (workspaceId, asOfDate) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/trial-balance`
        : '/api/v1/ledger/trial-balance';
      const res = await axios.get<TrialBalanceResponse>(url, {
        params: asOfDate ? { as_of_date: asOfDate } : {},
      });
      set({ trialBalance: res.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail?.message || err.message || 'Failed to fetch trial balance',
        isLoading: false,
      });
    }
  },

  getJournal: async (journalId, workspaceId) => {
    const url = workspaceId
      ? `/api/v1/workspaces/${workspaceId}/ledger/journals/${journalId}`
      : `/api/v1/ledger/journals/${journalId}`;
    const res = await axios.get<JournalEntryResponse>(url);
    set({ selectedJournal: res.data });
    return res.data;
  },

  createJournal: async (payload, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/journals`
        : '/api/v1/ledger/journals';
      const res = await axios.post<JournalEntryResponse>(url, payload);
      set((state) => ({
        journals: [res.data, ...state.journals],
        totalJournals: state.totalJournals + 1,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to create journal entry';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  postJournal: async (journalId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/journals/${journalId}/post`
        : `/api/v1/ledger/journals/${journalId}/post`;
      const res = await axios.post<JournalEntryResponse>(url);
      set((state) => ({
        journals: state.journals.map((j) => (j.id === journalId ? res.data : j)),
        selectedJournal: res.data,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to post journal entry';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  reverseJournal: async (journalId, reason, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/journals/${journalId}/reverse`
        : `/api/v1/ledger/journals/${journalId}/reverse`;
      const res = await axios.post<JournalEntryResponse>(url, { reason });
      set((state) => ({
        journals: [res.data, ...state.journals.map((j) => (j.id === journalId ? { ...j, status: 'reversed' } : j))],
        totalJournals: state.totalJournals + 1,
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to reverse journal entry';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  createAccount: async (payload, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/ledger/accounts`
        : '/api/v1/ledger/accounts';
      const res = await axios.post<LedgerAccountResponse>(url, payload);
      set((state) => ({
        accounts: [...state.accounts, res.data].sort((a, b) => a.code.localeCompare(b.code)),
        isLoading: false,
      }));
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || err.message || 'Failed to create ledger account';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },
}));
