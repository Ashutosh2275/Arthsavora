import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  FamilyProfileDTO,
  UpdateFamilyProfileDTO,
  FamilyMemberDTO,
  FamilyAllocationDTO,
  CreateAllocationDTO,
  FamilyContributionDTO,
  RecordContributionDTO,
  FamilySettlementSummaryDTO,
  SharedAccountDTO,
  FamilyActivityDTO,
  FamilyOverviewDTO,
} from '@arthsavora/contracts';

interface FamilyState {
  overview: FamilyOverviewDTO | null;
  profile: FamilyProfileDTO | null;
  members: FamilyMemberDTO[];
  allocations: FamilyAllocationDTO[];
  totalAllocations: number;
  contributions: FamilyContributionDTO[];
  totalContributions: number;
  settlement: FamilySettlementSummaryDTO | null;
  sharedAccounts: SharedAccountDTO[];
  activities: FamilyActivityDTO[];
  totalActivities: number;
  isLoading: boolean;
  error: string | null;

  clearError: () => void;
  fetchOverview: (workspaceId?: string) => Promise<void>;
  fetchProfile: (workspaceId?: string) => Promise<void>;
  updateProfile: (data: UpdateFamilyProfileDTO, workspaceId?: string) => Promise<void>;
  fetchMembers: (workspaceId?: string) => Promise<void>;
  inviteMember: (email: string, role: string, workspaceId?: string) => Promise<any>;
  updateMemberRole: (memberId: string, role: string, workspaceId?: string) => Promise<void>;
  removeMember: (memberId: string, workspaceId?: string) => Promise<void>;
  fetchAllocations: (workspaceId?: string, status?: string) => Promise<void>;
  createAllocation: (data: CreateAllocationDTO, workspaceId?: string) => Promise<FamilyAllocationDTO>;
  fetchContributions: (workspaceId?: string, period?: string, memberId?: string) => Promise<void>;
  recordContribution: (data: RecordContributionDTO, workspaceId?: string) => Promise<FamilyContributionDTO>;
  updateContribution: (
    id: string,
    data: { paid_amount_paise?: number; status?: string; notes?: string },
    workspaceId?: string
  ) => Promise<void>;
  fetchSettlements: (workspaceId?: string, period?: string) => Promise<void>;
  fetchSharedAccounts: (workspaceId?: string) => Promise<void>;
  shareAccount: (accountId: string, scope?: string, notes?: string, workspaceId?: string) => Promise<void>;
  revokeSharedAccount: (accountId: string, workspaceId?: string) => Promise<void>;
  fetchActivities: (workspaceId?: string) => Promise<void>;
}

export const useFamilyStore = create<FamilyState>((set, get) => ({
  overview: null,
  profile: null,
  members: [],
  allocations: [],
  totalAllocations: 0,
  contributions: [],
  totalContributions: 0,
  settlement: null,
  sharedAccounts: [],
  activities: [],
  totalActivities: 0,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchOverview: async (workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.get('/api/v1/family/overview', { headers });
      set({ overview: res.data, profile: res.data.profile, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to load family overview.',
        isLoading: false,
      });
    }
  },

  fetchProfile: async (workspaceId?: string) => {
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.get('/api/v1/family/profile', { headers });
      set({ profile: res.data });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message });
    }
  },

  updateProfile: async (data: UpdateFamilyProfileDTO, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.put('/api/v1/family/profile', data, { headers });
      set({ profile: res.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to update family preferences.',
        isLoading: false,
      });
      throw err;
    }
  },

  fetchMembers: async (workspaceId?: string) => {
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.get('/api/v1/family/members', { headers });
      set({ members: res.data });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message });
    }
  },

  inviteMember: async (email: string, role: string, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.post('/api/v1/family/members/invite', { email, role }, { headers });
      set({ isLoading: false });
      return res.data;
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to issue family invitation.',
        isLoading: false,
      });
      throw err;
    }
  },

  updateMemberRole: async (memberId: string, role: string, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      await axios.patch(`/api/v1/family/members/${memberId}/role`, { role }, { headers });
      await get().fetchMembers(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to update member role.',
        isLoading: false,
      });
      throw err;
    }
  },

  removeMember: async (memberId: string, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      await axios.delete(`/api/v1/family/members/${memberId}`, { headers });
      await get().fetchMembers(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to revoke member access.',
        isLoading: false,
      });
      throw err;
    }
  },

  fetchAllocations: async (workspaceId?: string, status?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const params = status ? { status } : undefined;
      const res = await axios.get('/api/v1/family/allocations', { headers, params });
      set({
        allocations: res.data.items || [],
        totalAllocations: res.data.total || 0,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to load expense allocations.',
        isLoading: false,
      });
    }
  },

  createAllocation: async (data: CreateAllocationDTO, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.post('/api/v1/family/allocations', data, { headers });
      await get().fetchAllocations(workspaceId);
      set({ isLoading: false });
      return res.data;
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to create expense allocation.',
        isLoading: false,
      });
      throw err;
    }
  },

  fetchContributions: async (workspaceId?: string, period?: string, memberId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const params: Record<string, string> = {};
      if (period) params.period = period;
      if (memberId) params.member_user_id = memberId;
      const res = await axios.get('/api/v1/family/contributions', { headers, params });
      set({
        contributions: res.data.items || [],
        totalContributions: res.data.total || 0,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to load member contributions.',
        isLoading: false,
      });
    }
  },

  recordContribution: async (data: RecordContributionDTO, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.post('/api/v1/family/contributions', data, { headers });
      await get().fetchContributions(workspaceId);
      set({ isLoading: false });
      return res.data;
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to record contribution.',
        isLoading: false,
      });
      throw err;
    }
  },

  updateContribution: async (
    id: string,
    data: { paid_amount_paise?: number; status?: string; notes?: string },
    workspaceId?: string
  ) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      await axios.patch(`/api/v1/family/contributions/${id}`, data, { headers });
      await get().fetchContributions(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to update contribution.',
        isLoading: false,
      });
      throw err;
    }
  },

  fetchSettlements: async (workspaceId?: string, period?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const params = period ? { period } : undefined;
      const res = await axios.get('/api/v1/family/settlements', { headers, params });
      set({ settlement: res.data, isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to calculate settlements.',
        isLoading: false,
      });
    }
  },

  fetchSharedAccounts: async (workspaceId?: string) => {
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.get('/api/v1/family/shared-accounts', { headers });
      set({ sharedAccounts: res.data || [] });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message });
    }
  },

  shareAccount: async (accountId: string, scope = 'balance_only', notes?: string, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      await axios.post('/api/v1/family/shared-accounts', { account_id: accountId, share_scope: scope, notes }, { headers });
      await get().fetchSharedAccounts(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to share personal account.',
        isLoading: false,
      });
      throw err;
    }
  },

  revokeSharedAccount: async (accountId: string, workspaceId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      await axios.delete(`/api/v1/family/shared-accounts/${accountId}`, { headers });
      await get().fetchSharedAccounts(workspaceId);
      set({ isLoading: false });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || err.message || 'Failed to revoke shared account.',
        isLoading: false,
      });
      throw err;
    }
  },

  fetchActivities: async (workspaceId?: string) => {
    try {
      const headers = workspaceId ? { 'X-Workspace-ID': workspaceId } : undefined;
      const res = await axios.get('/api/v1/family/activity', { headers });
      set({
        activities: res.data.items || [],
        totalActivities: res.data.total || 0,
      });
    } catch (err: any) {
      set({ error: err.response?.data?.detail || err.message });
    }
  },
}));
