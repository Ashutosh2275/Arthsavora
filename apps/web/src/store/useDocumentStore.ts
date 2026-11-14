import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  FinancialDocument,
  DocumentExtractionResult,
  TransactionMatchCandidate,
  DocumentCorrectionRequest,
  DocumentConfirmRequest,
  DocumentMatchAssociateRequest,
} from '@arthsavora/contracts';

interface DocumentState {
  documents: FinancialDocument[];
  totalDocuments: number;
  selectedDocument: FinancialDocument | null;
  matches: TransactionMatchCandidate[];
  isLoading: boolean;
  isUploading: boolean;
  isProcessing: boolean;
  isMatching: boolean;
  error: string | null;

  clearError: () => void;
  setSelectedDocument: (doc: FinancialDocument | null) => void;
  fetchDocuments: (
    workspaceId?: string,
    filters?: { status?: string; documentType?: string; search?: string; limit?: number; offset?: number }
  ) => Promise<void>;
  fetchDocumentDetails: (documentId: string, workspaceId?: string) => Promise<FinancialDocument>;
  uploadDocument: (
    file: File,
    workspaceId?: string,
    documentType?: string,
    autoProcess?: boolean,
    ocrProvider?: string
  ) => Promise<FinancialDocument>;
  processDocument: (documentId: string, workspaceId?: string, ocrProvider?: string) => Promise<FinancialDocument>;
  correctExtraction: (
    documentId: string,
    corrections: Record<string, any>,
    notes?: string,
    workspaceId?: string
  ) => Promise<FinancialDocument>;
  confirmTransaction: (
    documentId: string,
    accountId: string,
    confirmedData?: Record<string, any>,
    notes?: string,
    workspaceId?: string
  ) => Promise<any>;
  findMatches: (documentId: string, workspaceId?: string) => Promise<TransactionMatchCandidate[]>;
  associateTransaction: (
    documentId: string,
    transactionId: string,
    matchScore?: number,
    notes?: string,
    workspaceId?: string
  ) => Promise<any>;
  rejectDocument: (documentId: string, notes?: string, workspaceId?: string) => Promise<FinancialDocument>;
  deleteDocument: (documentId: string, workspaceId?: string) => Promise<void>;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  totalDocuments: 0,
  selectedDocument: null,
  matches: [],
  isLoading: false,
  isUploading: false,
  isProcessing: false,
  isMatching: false,
  error: null,

  clearError: () => set({ error: null }),
  setSelectedDocument: (doc) => set({ selectedDocument: doc }),

  fetchDocuments: async (workspaceId, filters) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId ? `/api/v1/workspaces/${workspaceId}/documents` : '/api/v1/documents';
      const params: Record<string, any> = {};
      if (filters?.status) params.status = filters.status;
      if (filters?.documentType) params.document_type = filters.documentType;
      if (filters?.search) params.search = filters.search;
      if (filters?.limit) params.limit = filters.limit;
      if (filters?.offset) params.offset = filters.offset;

      const res = await axios.get(url, { params });
      set({
        documents: res.data.items || [],
        totalDocuments: res.data.total || 0,
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string; error?: { message?: string } } } })?.response?.data
          ?.detail ||
        (err as { response?: { data?: { detail?: string; error?: { message?: string } } } })?.response?.data
          ?.error?.message ||
        'Failed to fetch financial documents.';
      set({ error: msg, isLoading: false });
    }
  },

  fetchDocumentDetails: async (documentId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}`
        : `/api/v1/documents/${documentId}`;
      const res = await axios.get(url);
      const doc = res.data;
      set({ selectedDocument: doc, isLoading: false });
      return doc;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to fetch document details.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  uploadDocument: async (file, workspaceId, documentType = 'receipt', autoProcess = true, ocrProvider) => {
    set({ isUploading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/upload`
        : '/api/v1/documents/upload';
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', documentType);
      formData.append('auto_process', autoProcess ? 'true' : 'false');
      if (ocrProvider) formData.append('ocr_provider', ocrProvider);

      const res = await axios.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const doc = res.data;
      set((state) => ({
        documents: [doc, ...state.documents.filter((d) => d.id !== doc.id)],
        selectedDocument: doc,
        isUploading: false,
      }));
      return doc;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string; error?: { message?: string } } } })?.response?.data
          ?.detail ||
        (err as { response?: { data?: { detail?: string; error?: { message?: string } } } })?.response?.data
          ?.error?.message ||
        'Failed to upload receipt file.';
      set({ error: msg, isUploading: false });
      throw err;
    }
  },

  processDocument: async (documentId, workspaceId, ocrProvider) => {
    set({ isProcessing: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/process`
        : `/api/v1/documents/${documentId}/process`;
      const res = await axios.post(url, null, {
        params: ocrProvider ? { ocr_provider: ocrProvider } : {},
      });
      const doc = res.data;
      set((state) => ({
        documents: state.documents.map((d) => (d.id === doc.id ? doc : d)),
        selectedDocument: doc,
        isProcessing: false,
      }));
      return doc;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to process document.';
      set({ error: msg, isProcessing: false });
      throw err;
    }
  },

  correctExtraction: async (documentId, corrections, notes, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/extraction`
        : `/api/v1/documents/${documentId}/extraction`;
      const res = await axios.patch(url, {
        corrected_data: corrections,
        notes,
      });
      const doc = res.data;
      set((state) => ({
        documents: state.documents.map((d) => (d.id === doc.id ? doc : d)),
        selectedDocument: doc,
        isLoading: false,
      }));
      return doc;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to submit corrections.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  confirmTransaction: async (documentId, accountId, confirmedData, notes, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/confirm`
        : `/api/v1/documents/${documentId}/confirm`;
      const res = await axios.post(url, {
        account_id: accountId,
        confirmed_data: confirmedData,
        notes,
      });
      await get().fetchDocumentDetails(documentId, workspaceId);
      set({ isLoading: false });
      return res.data;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to confirm and create transaction.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  findMatches: async (documentId, workspaceId) => {
    set({ isMatching: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/match`
        : `/api/v1/documents/${documentId}/match`;
      const res = await axios.post(url);
      const matches = res.data || [];
      set({ matches, isMatching: false });
      return matches;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to scan for transaction matches.';
      set({ error: msg, isMatching: false });
      return [];
    }
  },

  associateTransaction: async (documentId, transactionId, matchScore, notes, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/associate`
        : `/api/v1/documents/${documentId}/associate`;
      const res = await axios.post(url, {
        transaction_id: transactionId,
        match_score: matchScore,
        notes,
      });
      await get().fetchDocumentDetails(documentId, workspaceId);
      set({ isLoading: false });
      return res.data;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to associate document with transaction.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  rejectDocument: async (documentId, notes, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}/reject`
        : `/api/v1/documents/${documentId}/reject`;
      const res = await axios.post(url, null, {
        params: notes ? { notes } : {},
      });
      const doc = res.data;
      set((state) => ({
        documents: state.documents.map((d) => (d.id === doc.id ? doc : d)),
        selectedDocument: doc,
        isLoading: false,
      }));
      return doc;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to reject document.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  deleteDocument: async (documentId, workspaceId) => {
    set({ isLoading: true, error: null });
    try {
      const url = workspaceId
        ? `/api/v1/workspaces/${workspaceId}/documents/${documentId}`
        : `/api/v1/documents/${documentId}`;
      await axios.delete(url);
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== documentId),
        selectedDocument: state.selectedDocument?.id === documentId ? null : state.selectedDocument,
        isLoading: false,
      }));
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to delete document.';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },
}));
