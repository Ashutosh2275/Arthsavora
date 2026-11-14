import { create } from 'zustand';
import axios from '../lib/axios';
import {
  ImportBatchResponse,
  ImportCandidateResponse,
  ImportCandidateUpdateRequest,
  ImportConfirmResponse,
  ImportJobSummary,
  ImportReconciliationReport,
  ImportUploadResponse,
} from '@arthsavora/contracts';

interface ImportState {
  jobs: ImportJobSummary[];
  currentJob: ImportJobSummary | null;
  currentBatch: ImportBatchResponse | null;
  candidates: ImportCandidateResponse[];
  totalCandidates: number;
  lastUploadResult: ImportUploadResponse | null;
  reconciliation: ImportReconciliationReport | null;
  isLoading: boolean;
  isUploading: boolean;
  isConfirming: boolean;
  error: string | null;

  fetchJobs: (workspaceId?: string, status?: string) => Promise<void>;
  fetchJob: (jobId: string, workspaceId?: string) => Promise<ImportJobSummary>;
  uploadFile: (
    file: File,
    workspaceId?: string,
    accountId?: string,
    columnMapping?: Record<string, string>,
    sheetName?: string,
    allowDuplicate?: boolean,
  ) => Promise<ImportUploadResponse>;
  fetchCandidates: (
    batchId: string,
    workspaceId?: string,
    filters?: { validation_status?: string; duplicate_status?: string; review_status?: string; limit?: number; offset?: number },
  ) => Promise<void>;
  updateCandidate: (
    candidateId: string,
    updates: ImportCandidateUpdateRequest,
    workspaceId?: string,
  ) => Promise<ImportCandidateResponse>;
  toggleCandidateSelection: (candidateId: string, selected: boolean, workspaceId?: string) => Promise<void>;
  toggleSelectAll: (selected: boolean) => void;
  confirmImport: (
    jobId: string,
    batchId: string,
    targetAccountId?: string,
    workspaceId?: string,
  ) => Promise<ImportConfirmResponse>;
  cancelJob: (jobId: string, workspaceId?: string) => Promise<void>;
  fetchReconciliation: (batchId: string, workspaceId?: string) => Promise<ImportReconciliationReport>;
  clearError: () => void;
  resetCurrentUpload: () => void;
}

export const useImportStore = create<ImportState>((set, get) => ({
  jobs: [],
  currentJob: null,
  currentBatch: null,
  candidates: [],
  totalCandidates: 0,
  lastUploadResult: null,
  reconciliation: null,
  isLoading: false,
  isUploading: false,
  isConfirming: false,
  error: null,

  clearError: () => set({ error: null }),
  resetCurrentUpload: () => set({ lastUploadResult: null, candidates: [], totalCandidates: 0, currentJob: null, currentBatch: null }),

  fetchJobs: async (workspaceId, status) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId ? `/api/v1/workspaces/${workspaceId}/imports/jobs` : '/api/v1/imports/jobs';
      const params: Record<string, string> = {};
      if (status) params.status = status;
      const res = await axios.get(url, { params });
      set({ jobs: res.data.items || [], isLoading: false });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to fetch import jobs';
      set({ error: msg, isLoading: false });
    }
  },

  fetchJob: async (jobId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId ? `/api/v1/workspaces/${workspaceId}/imports/jobs/${jobId}` : `/api/v1/imports/jobs/${jobId}`;
      const res = await axios.get(url);
      set({ currentJob: res.data, isLoading: false });
      return res.data;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to fetch job details';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  uploadFile: async (file, workspaceId, accountId, columnMapping, sheetName, allowDuplicate) => {
    set({ isUploading: true, error: null });
    try {
      const url = workspaceId ? `/api/v1/workspaces/${workspaceId}/imports/upload` : '/api/v1/imports/upload';
      const formData = new FormData();
      formData.append('file', file);
      if (accountId) formData.append('account_id', accountId);
      if (columnMapping) formData.append('column_mapping', JSON.stringify(columnMapping));
      if (sheetName) formData.append('sheet_name', sheetName);
      if (allowDuplicate) formData.append('allow_duplicate_file', 'true');

      const res = await axios.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data: ImportUploadResponse = res.data;
      set({
        lastUploadResult: data,
        isUploading: false,
      });

      // Automatically fetch full candidates for the created batch
      if (data.batch_id) {
        await get().fetchCandidates(data.batch_id, workspaceId);
      }
      return data;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to upload statement';
      set({ error: msg, isUploading: false });
      throw err;
    }
  },

  fetchCandidates: async (batchId, workspaceId, filters) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/imports/batches/${batchId}/candidates`
        : `/api/v1/imports/batches/${batchId}/candidates`;
      const res = await axios.get(url, { params: filters });
      set({
        candidates: res.data.items || [],
        totalCandidates: res.data.total || 0,
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to fetch candidates';
      set({ error: msg, isLoading: false });
    }
  },

  updateCandidate: async (candidateId, updates, workspaceId) => {
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/imports/candidates/${candidateId}`
        : `/api/v1/imports/candidates/${candidateId}`;
      const res = await axios.patch(url, updates);
      const updated: ImportCandidateResponse = res.data;
      set((state) => ({
        candidates: state.candidates.map((c) => (c.id === candidateId ? updated : c)),
      }));
      return updated;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to update candidate';
      set({ error: msg });
      throw err;
    }
  },

  toggleCandidateSelection: async (candidateId, selected, workspaceId) => {
    // Optimistic UI update
    set((state) => ({
      candidates: state.candidates.map((c) => (c.id === candidateId ? { ...c, selected_for_import: selected } : c)),
    }));
    await get().updateCandidate(candidateId, { selected_for_import: selected }, workspaceId);
  },

  toggleSelectAll: (selected) => {
    set((state) => ({
      candidates: state.candidates.map((c) =>
        c.validation_status === 'valid' ? { ...c, selected_for_import: selected } : c,
      ),
    }));
  },

  confirmImport: async (jobId, batchId, targetAccountId, workspaceId) => {
    set({ isConfirming: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/imports/jobs/${jobId}/batches/${batchId}/confirm`
        : `/api/v1/imports/jobs/${jobId}/batches/${batchId}/confirm`;
      const res = await axios.post(url, { target_account_id: targetAccountId });
      set({ isConfirming: false });
      return res.data;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to confirm import';
      set({ error: msg, isConfirming: false });
      throw err;
    }
  },

  cancelJob: async (jobId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/imports/jobs/${jobId}/cancel`
        : `/api/v1/imports/jobs/${jobId}/cancel`;
      await axios.post(url);
      set({ isLoading: false, lastUploadResult: null, candidates: [] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to cancel job';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  fetchReconciliation: async (batchId, workspaceId) => {
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/imports/batches/${batchId}/reconciliation`
        : `/api/v1/imports/batches/${batchId}/reconciliation`;
      const res = await axios.get(url);
      set({ reconciliation: res.data });
      return res.data;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || 'Failed to fetch reconciliation';
      set({ error: msg });
      throw err;
    }
  },
}));
