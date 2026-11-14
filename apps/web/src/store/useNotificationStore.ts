import { create } from 'zustand';
import axios from '../lib/axios';
import type {
  NotificationResponse,
  NotificationPreferenceResponse,
  NotificationPreferenceUpdateRequest,
  PushSubscriptionResponse,
} from '@arthsavora/contracts';

interface NotificationFilterOptions {
  category?: string;
  severity?: string;
  is_read?: boolean;
  is_archived?: boolean;
  limit?: number;
  offset?: number;
}

interface NotificationState {
  notifications: NotificationResponse[];
  total: number;
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  activeCategory: string; // 'all', 'unread', or category name
  preferences: NotificationPreferenceResponse[];
  pushSubscriptions: PushSubscriptionResponse[];
  isPushSupported: boolean;
  pushPermission: string;

  // Actions
  clearError: () => void;
  setActiveCategory: (cat: string) => void;
  fetchNotifications: (workspaceId?: string, options?: NotificationFilterOptions) => Promise<void>;
  fetchUnreadCount: (workspaceId?: string) => Promise<number>;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: (workspaceId?: string, category?: string) => Promise<void>;
  archiveNotification: (notificationId: string) => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<void>;
  fetchPreferences: () => Promise<void>;
  updatePreference: (payload: NotificationPreferenceUpdateRequest) => Promise<void>;
  fetchPushSubscriptions: () => Promise<void>;
  registerPushSubscription: (endpoint: string, p256dhKey: string, authKey: string) => Promise<void>;
  revokePushSubscription: (subscriptionId: string) => Promise<void>;
  triggerTestNotification: (category?: string, severity?: string) => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  total: 0,
  unreadCount: 0,
  isLoading: false,
  error: null,
  activeCategory: 'all',
  preferences: [],
  pushSubscriptions: [],
  isPushSupported: typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window,
  pushPermission: typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default',

  clearError: () => set({ error: null }),

  setActiveCategory: (cat: string) => {
    set({ activeCategory: cat });
    get().fetchNotifications();
  },

  fetchNotifications: async (workspaceId?: string, options?: NotificationFilterOptions) => {
    set({ isLoading: true, error: null });
    try {
      const activeCat = get().activeCategory;
      const params: Record<string, any> = {
        limit: options?.limit ?? 50,
        offset: options?.offset ?? 0,
        is_archived: options?.is_archived ?? false,
      };

      if (workspaceId) {
        params.workspace_id = workspaceId;
      }

      if (activeCat === 'unread') {
        params.is_read = false;
      } else if (activeCat !== 'all' && activeCat !== 'settings') {
        params.category = activeCat;
      }

      if (options?.severity) {
        params.severity = options.severity;
      }
      if (options?.is_read !== undefined && activeCat !== 'unread') {
        params.is_read = options.is_read;
      }

      const res = await axios.get('/notifications', { params });
      set({
        notifications: res.data.items || [],
        total: res.data.total || 0,
        unreadCount: res.data.unread_count ?? 0,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.message || err.message || 'Failed to fetch notifications',
        isLoading: false,
      });
    }
  },

  fetchUnreadCount: async (workspaceId?: string) => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await axios.get('/notifications/unread-count', { params });
      const count = res.data.unread_count ?? 0;
      set({ unreadCount: count });
      return count;
    } catch (err) {
      return 0;
    }
  },

  markAsRead: async (notificationId: string) => {
    try {
      await axios.post(`/notifications/${notificationId}/read`);
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to mark notification as read' });
    }
  },

  markAllAsRead: async (workspaceId?: string, category?: string) => {
    try {
      const params: Record<string, any> = {};
      if (workspaceId) params.workspace_id = workspaceId;
      if (category && category !== 'all' && category !== 'unread') params.category = category;

      await axios.post('/notifications/read-all', null, { params });
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() })),
        unreadCount: 0,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to mark all as read' });
    }
  },

  archiveNotification: async (notificationId: string) => {
    try {
      await axios.post(`/notifications/${notificationId}/archive`);
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== notificationId),
        total: Math.max(0, state.total - 1),
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to archive notification' });
    }
  },

  deleteNotification: async (notificationId: string) => {
    try {
      await axios.delete(`/notifications/${notificationId}`);
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== notificationId),
        total: Math.max(0, state.total - 1),
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to delete notification' });
    }
  },

  fetchPreferences: async () => {
    try {
      const res = await axios.get('/notifications/preferences');
      set({ preferences: res.data || [] });
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to load preferences' });
    }
  },

  updatePreference: async (payload: NotificationPreferenceUpdateRequest) => {
    try {
      const res = await axios.patch('/notifications/preferences', payload);
      set((state) => ({
        preferences: [
          ...state.preferences.filter(
            (p) => !(p.category === payload.category && p.channel === payload.channel)
          ),
          res.data,
        ],
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to update preference' });
    }
  },

  fetchPushSubscriptions: async () => {
    try {
      const res = await axios.get('/notifications/push-subscriptions');
      set({ pushSubscriptions: res.data || [] });
    } catch (err) {
      // Ignored
    }
  },

  registerPushSubscription: async (endpoint: string, p256dhKey: string, authKey: string) => {
    try {
      const res = await axios.post('/notifications/push-subscriptions', {
        endpoint,
        p256dh_key: p256dhKey,
        auth_key: authKey,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
      });
      set((state) => ({
        pushSubscriptions: [...state.pushSubscriptions, res.data],
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to register push subscription' });
    }
  },

  revokePushSubscription: async (subscriptionId: string) => {
    try {
      await axios.delete(`/notifications/push-subscriptions/${subscriptionId}`);
      set((state) => ({
        pushSubscriptions: state.pushSubscriptions.filter((s) => s.id !== subscriptionId),
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to revoke push subscription' });
    }
  },

  triggerTestNotification: async (category = 'transaction', severity = 'info') => {
    try {
      const res = await axios.post('/notifications/test', {
        category,
        title: `Test ${category.toUpperCase()} Alert`,
        message: 'This is a test notification generated from ARTHSAVORA Notification Center.',
        severity,
      });
      set((state) => ({
        notifications: [res.data, ...state.notifications],
        unreadCount: state.unreadCount + 1,
        total: state.total + 1,
      }));
    } catch (err: any) {
      set({ error: err.response?.data?.message || err.message || 'Failed to trigger test alert' });
    }
  },
}));
