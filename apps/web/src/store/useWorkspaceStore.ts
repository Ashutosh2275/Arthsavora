import { create } from 'zustand';
import api from '@/lib/axios';
import type {
  WorkspaceResponse,
  WorkspaceCreateRequest,
  WorkspaceUpdateRequest,
  WorkspaceMemberResponse,
} from '@arthsavora/contracts';

interface WorkspaceState {
  workspaces: WorkspaceResponse[];
  activeWorkspace: WorkspaceResponse | null;
  activeWorkspaceId: string | null;
  members: WorkspaceMemberResponse[];
  isLoading: boolean;
  error: string | null;

  fetchWorkspaces: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (payload: WorkspaceCreateRequest) => Promise<WorkspaceResponse>;
  updateWorkspace: (workspaceId: string, payload: WorkspaceUpdateRequest) => Promise<WorkspaceResponse>;
  fetchMembers: (workspaceId: string) => Promise<WorkspaceMemberResponse[]>;
  inviteMember: (workspaceId: string, email: string, role: string) => Promise<void>;
  removeMember: (workspaceId: string, membershipId: string) => Promise<void>;
  updateMemberRole: (workspaceId: string, membershipId: string, role: string) => Promise<void>;
}

// Global cache invalidation hooks registered by feature stores
type InvalidationCallback = () => void;
const cacheInvalidationCallbacks: Set<InvalidationCallback> = new Set();

export const registerWorkspaceResetCallback = (cb: InvalidationCallback) => {
  cacheInvalidationCallbacks.add(cb);
  return () => {
    cacheInvalidationCallbacks.delete(cb);
  };
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  activeWorkspace: null,
  activeWorkspaceId: typeof window !== 'undefined' ? localStorage.getItem('active_workspace_id') : null,
  members: [],
  isLoading: false,
  error: null,

  fetchWorkspaces: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.get('/workspaces');
      const workspaces: WorkspaceResponse[] = res.data;
      const currentActiveId = get().activeWorkspaceId;

      let active: WorkspaceResponse | null = null;
      if (currentActiveId) {
        active = workspaces.find((w) => w.id === currentActiveId) || null;
      }
      if (!active && workspaces.length > 0) {
        // Default to personal workspace if present, else first workspace
        active = workspaces.find((w) => w.type.toLowerCase() === 'personal') || workspaces[0];
      }

      const activeId = active ? String(active.id) : null;
      if (activeId && typeof window !== 'undefined') {
        localStorage.setItem('active_workspace_id', activeId);
      }

      set({
        workspaces,
        activeWorkspace: active,
        activeWorkspaceId: activeId,
        isLoading: false,
      });
    } catch (err: any) {
      console.error('Failed to fetch workspaces:', err);
      set({
        error: err.response?.data?.message || err.message || 'Failed to fetch workspaces',
        isLoading: false,
      });
    }
  },

  switchWorkspace: async (workspaceId: string) => {
    const { workspaces } = get();
    const target = workspaces.find((w) => String(w.id) === String(workspaceId));
    if (!target) return;

    if (typeof window !== 'undefined') {
      localStorage.setItem('active_workspace_id', String(target.id));
    }

    set({
      activeWorkspace: target,
      activeWorkspaceId: String(target.id),
      members: [],
    });

    // Notify all registered stores to invalidate/clear their tenant-dependent cache
    cacheInvalidationCallbacks.forEach((cb) => {
      try {
        cb();
      } catch (e) {
        console.warn('Error in workspace reset callback:', e);
      }
    });
  },

  createWorkspace: async (payload: WorkspaceCreateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post('/workspaces', payload);
      const newWorkspace: WorkspaceResponse = res.data;
      const updated = [...get().workspaces, newWorkspace];

      if (typeof window !== 'undefined') {
        localStorage.setItem('active_workspace_id', String(newWorkspace.id));
      }

      set({
        workspaces: updated,
        activeWorkspace: newWorkspace,
        activeWorkspaceId: String(newWorkspace.id),
        isLoading: false,
      });

      return newWorkspace;
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to create workspace';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  updateWorkspace: async (workspaceId: string, payload: WorkspaceUpdateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.patch(`/workspaces/${workspaceId}`, payload);
      const updated: WorkspaceResponse = res.data;
      const workspaces = get().workspaces.map((w) => (String(w.id) === String(workspaceId) ? updated : w));
      const activeWorkspace = String(get().activeWorkspaceId) === String(workspaceId) ? updated : get().activeWorkspace;

      set({ workspaces, activeWorkspace, isLoading: false });
      return updated;
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to update workspace';
      set({ error: msg, isLoading: false });
      throw new Error(msg);
    }
  },

  fetchMembers: async (workspaceId: string) => {
    try {
      const res = await api.get(`/workspaces/${workspaceId}/members`);
      const members: WorkspaceMemberResponse[] = res.data;
      set({ members });
      return members;
    } catch (err: any) {
      console.error('Failed to fetch members:', err);
      return [];
    }
  },

  inviteMember: async (workspaceId: string, email: string, role: string) => {
    try {
      await api.post(`/workspaces/${workspaceId}/invitations`, { email, role });
      await get().fetchMembers(workspaceId);
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to send invitation';
      throw new Error(msg);
    }
  },

  removeMember: async (workspaceId: string, membershipId: string) => {
    try {
      await api.delete(`/workspaces/${workspaceId}/members/${membershipId}`);
      set({
        members: get().members.filter((m) => String(m.id) !== String(membershipId)),
      });
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to remove member';
      throw new Error(msg);
    }
  },

  updateMemberRole: async (workspaceId: string, membershipId: string, role: string) => {
    try {
      await api.patch(`/workspaces/${workspaceId}/members/${membershipId}`, { role });
      await get().fetchMembers(workspaceId);
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to update member role';
      throw new Error(msg);
    }
  },
}));

export default useWorkspaceStore;
