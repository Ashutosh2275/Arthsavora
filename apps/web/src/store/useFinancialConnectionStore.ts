import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  DiscoveredAccountDTO,
  FinancialConnectionDTO,
  FinancialProviderDTO,
  InitiateConnectionPayload,
  LinkAccountPayload,
  ReconciliationRecordDTO,
  ResolveReconciliationPayload,
  SyncJobDTO,
} from '@arthsavora/contracts';

interface FinancialConnectionState {
  providers: FinancialProviderDTO[];
  connections: FinancialConnectionDTO[];
  selectedConnection: FinancialConnectionDTO | null;
  syncHistory: Record<string, SyncJobDTO[]>;
  reconciliations: Record<string, ReconciliationRecordDTO[]>;
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  setSelectedConnection: (connection: FinancialConnectionDTO | null) => void;
  fetchProviders: () => Promise<void>;
  fetchConnections: () => Promise<void>;
  initiateConnection: (payload: InitiateConnectionPayload) => Promise<FinancialConnectionDTO>;
  authorizeConnection: (connectionId: string, providerConsentHandle?: string) => Promise<FinancialConnectionDTO>;
  triggerSync: (connectionId: string, jobType?: string) => Promise<SyncJobDTO>;
  revokeConsent: (connectionId: string, reason?: string) => Promise<void>;
  disconnectConnection: (connectionId: string) => Promise<void>;
  linkAccount: (connectionId: string, refId: string, payload: LinkAccountPayload) => Promise<DiscoveredAccountDTO>;
  unlinkAccount: (connectionId: string, refId: string) => Promise<DiscoveredAccountDTO>;
  fetchSyncHistory: (connectionId: string) => Promise<void>;
  fetchReconciliations: (connectionId: string) => Promise<void>;
  resolveReconciliation: (connectionId: string, recId: string, explanation: string) => Promise<void>;
}

export const useFinancialConnectionStore = create<FinancialConnectionState>((set, get) => ({
  providers: [],
  connections: [],
  selectedConnection: null,
  syncHistory: {},
  reconciliations: {},
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),
  setSelectedConnection: (connection) => set({ selectedConnection: connection }),

  fetchProviders: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.get<FinancialProviderDTO[]>('/financial-providers');
      set({ providers: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch providers',
        isLoading: false,
      });
    }
  },

  fetchConnections: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.get<FinancialConnectionDTO[]>('/financial-connections');
      set({ connections: response.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to fetch connections',
        isLoading: false,
      });
    }
  },

  initiateConnection: async (payload: InitiateConnectionPayload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<FinancialConnectionDTO>('/financial-connections', payload);
      set((state) => ({
        connections: [response.data, ...state.connections],
        selectedConnection: response.data,
        isLoading: false,
      }));
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to initiate connection';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  authorizeConnection: async (connectionId: string, providerConsentHandle?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<FinancialConnectionDTO>(`/financial-connections/${connectionId}/authorize`, {
        provider_consent_handle: providerConsentHandle,
      });
      set((state) => ({
        connections: state.connections.map((c) => (c.id === connectionId ? response.data : c)),
        selectedConnection: response.data,
        isLoading: false,
      }));
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to authorize connection';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  triggerSync: async (connectionId: string, jobType: string = 'manual_sync') => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<SyncJobDTO>(`/financial-connections/${connectionId}/sync`, {
        job_type: jobType,
      });
      await get().fetchConnections();
      await get().fetchSyncHistory(connectionId);
      await get().fetchReconciliations(connectionId);
      set({ isLoading: false });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to trigger sync';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  revokeConsent: async (connectionId: string, reason?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<FinancialConnectionDTO>(`/financial-connections/${connectionId}/revoke`, {
        reason: reason || 'User requested revocation',
      });
      set((state) => ({
        connections: state.connections.map((c) => (c.id === connectionId ? response.data : c)),
        selectedConnection: response.data,
        isLoading: false,
      }));
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to revoke consent',
        isLoading: false,
      });
    }
  },

  disconnectConnection: async (connectionId: string) => {
    set({ isLoading: true, error: null });
    try {
      await axios.delete(`/financial-connections/${connectionId}`);
      set((state) => ({
        connections: state.connections.filter((c) => c.id !== connectionId),
        selectedConnection: state.selectedConnection?.id === connectionId ? null : state.selectedConnection,
        isLoading: false,
      }));
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to disconnect connection',
        isLoading: false,
      });
    }
  },

  linkAccount: async (connectionId: string, refId: string, payload: LinkAccountPayload) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<DiscoveredAccountDTO>(
        `/financial-connections/${connectionId}/accounts/${refId}/link`,
        payload
      );
      await get().fetchConnections();
      set({ isLoading: false });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to link account';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  unlinkAccount: async (connectionId: string, refId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await axios.post<DiscoveredAccountDTO>(
        `/financial-connections/${connectionId}/accounts/${refId}/unlink`
      );
      await get().fetchConnections();
      set({ isLoading: false });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to unlink account';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  fetchSyncHistory: async (connectionId: string) => {
    try {
      const response = await axios.get<SyncJobDTO[]>(`/financial-connections/${connectionId}/sync-history`);
      set((state) => ({
        syncHistory: {
          ...state.syncHistory,
          [connectionId]: response.data,
        },
      }));
    } catch (err: any) {
      console.error('Failed to fetch sync history', err);
    }
  },

  fetchReconciliations: async (connectionId: string) => {
    try {
      const response = await axios.get<ReconciliationRecordDTO[]>(`/financial-connections/${connectionId}/reconciliation`);
      set((state) => ({
        reconciliations: {
          ...state.reconciliations,
          [connectionId]: response.data,
        },
      }));
    } catch (err: any) {
      console.error('Failed to fetch reconciliations', err);
    }
  },

  resolveReconciliation: async (connectionId: string, recId: string, explanation: string) => {
    set({ isLoading: true, error: null });
    try {
      await axios.post(`/financial-connections/${connectionId}/reconciliation/${recId}/resolve`, {
        explanation,
      });
      await get().fetchReconciliations(connectionId);
      set({ isLoading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to resolve reconciliation';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },
}));
