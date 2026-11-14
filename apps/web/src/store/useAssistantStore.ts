import { create } from 'zustand';
import type {
  AssistantActionConfirmResponse,
  AssistantConversation,
  AssistantMessage,
  AssistantUsageSummary,
} from '@arthsavora/contracts';
import api from '@/lib/axios';

interface AssistantState {
  conversations: AssistantConversation[];
  activeConversation: AssistantConversation | null;
  messages: AssistantMessage[];
  streamingContent: string;
  isStreaming: boolean;
  isLoading: boolean;
  isActionLoading: boolean;
  error: string | null;
  usage: AssistantUsageSummary | null;

  fetchConversations: () => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  createConversation: (title?: string) => Promise<AssistantConversation>;
  updateConversationTitle: (conversationId: string, title: string) => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  fetchMessages: (conversationId: string) => Promise<void>;
  sendMessage: (conversationId: string, content: string) => Promise<AssistantMessage>;
  confirmAction: (actionId: string, confirmationToken: string) => Promise<AssistantActionConfirmResponse>;
  cancelAction: (actionId: string) => Promise<void>;
  fetchUsage: () => Promise<void>;
  clearActiveConversation: () => void;
}

export const useAssistantStore = create<AssistantState>((set, get) => ({
  conversations: [],
  activeConversation: null,
  messages: [],
  streamingContent: '',
  isStreaming: false,
  isLoading: false,
  isActionLoading: false,
  error: null,
  usage: null,

  fetchConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.get('/v1/assistant/conversations');
      set({ conversations: res.data.data, isLoading: false });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to fetch conversations.',
      });
    }
  },

  selectConversation: async (conversationId: string) => {
    set({ isLoading: true, error: null, streamingContent: '', isStreaming: false });
    try {
      const convRes = await api.get(`/v1/assistant/conversations/${conversationId}`);
      const msgRes = await api.get(`/v1/assistant/conversations/${conversationId}/messages`);
      set({
        activeConversation: convRes.data.data,
        messages: msgRes.data.data,
        isLoading: false,
      });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to load conversation details.',
      });
    }
  },

  createConversation: async (title?: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post('/v1/assistant/conversations', { title });
      const newConv = res.data.data;
      set((state) => ({
        conversations: [newConv, ...state.conversations],
        activeConversation: newConv,
        messages: [],
        isLoading: false,
      }));
      return newConv;
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to create new conversation.',
      });
      throw err;
    }
  },

  updateConversationTitle: async (conversationId: string, title: string) => {
    try {
      const res = await api.patch(`/v1/assistant/conversations/${conversationId}`, { title });
      const updated = res.data.data;
      set((state) => ({
        conversations: state.conversations.map((c) => (c.id === conversationId ? updated : c)),
        activeConversation: state.activeConversation?.id === conversationId ? updated : state.activeConversation,
      }));
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to update conversation title.' });
      throw err;
    }
  },

  deleteConversation: async (conversationId: string) => {
    try {
      await api.delete(`/v1/assistant/conversations/${conversationId}`);
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== conversationId),
        activeConversation: state.activeConversation?.id === conversationId ? null : state.activeConversation,
        messages: state.activeConversation?.id === conversationId ? [] : state.messages,
      }));
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to delete conversation.' });
      throw err;
    }
  },

  fetchMessages: async (conversationId: string) => {
    try {
      const res = await api.get(`/v1/assistant/conversations/${conversationId}/messages`);
      set({ messages: res.data.data });
    } catch (err: any) {
      set({ error: err?.response?.data?.message || 'Failed to load messages.' });
    }
  },

  sendMessage: async (conversationId: string, content: string) => {
    const userMsgPlaceholder: AssistantMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId,
      workspace_id: get().activeConversation?.workspace_id || '',
      role: 'user',
      content,
      tool_calls: [],
      tool_results: [],
      structured_data: {},
      tokens_prompt: 0,
      tokens_completion: 0,
      latency_ms: 0,
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMsgPlaceholder],
      isLoading: true,
      error: null,
    }));

    try {
      const res = await api.post(`/v1/assistant/conversations/${conversationId}/messages`, {
        content,
      });
      const assistantMsg: AssistantMessage = res.data.data;

      set((state) => ({
        messages: [...state.messages.filter((m) => m.id !== userMsgPlaceholder.id), userMsgPlaceholder, assistantMsg],
        isLoading: false,
      }));

      // Update conversation title in list if it changed
      get().fetchConversations();
      return assistantMsg;
    } catch (err: any) {
      set({
        isLoading: false,
        error: err?.response?.data?.message || 'Failed to send message to assistant.',
      });
      throw err;
    }
  },

  confirmAction: async (actionId: string, confirmationToken: string) => {
    set({ isActionLoading: true, error: null });
    try {
      const res = await api.post(`/v1/assistant/actions/${actionId}/confirm`, {
        confirmation_token: confirmationToken,
      });
      const data: AssistantActionConfirmResponse = res.data.data;

      // Update message draft status locally
      set((state) => ({
        messages: state.messages.map((m) => {
          if (m.action_draft && m.action_draft.id === actionId) {
            return {
              ...m,
              action_draft: {
                ...m.action_draft,
                status: 'confirmed',
              },
            };
          }
          return m;
        }),
        isActionLoading: false,
      }));

      return data;
    } catch (err: any) {
      set({
        isActionLoading: false,
        error: err?.response?.data?.message || 'Failed to confirm action draft.',
      });
      throw err;
    }
  },

  cancelAction: async (actionId: string) => {
    set({ isActionLoading: true, error: null });
    try {
      await api.post(`/v1/assistant/actions/${actionId}/cancel`);

      // Update message draft status locally
      set((state) => ({
        messages: state.messages.map((m) => {
          if (m.action_draft && m.action_draft.id === actionId) {
            return {
              ...m,
              action_draft: {
                ...m.action_draft,
                status: 'cancelled',
              },
            };
          }
          return m;
        }),
        isActionLoading: false,
      }));
    } catch (err: any) {
      set({
        isActionLoading: false,
        error: err?.response?.data?.message || 'Failed to cancel action draft.',
      });
      throw err;
    }
  },

  fetchUsage: async () => {
    try {
      const res = await api.get('/v1/assistant/usage');
      set({ usage: res.data.data });
    } catch (err: any) {
      // Non-blocking telemetry
      console.warn('Failed to fetch assistant usage metrics:', err);
    }
  },

  clearActiveConversation: () => {
    set({ activeConversation: null, messages: [], streamingContent: '', isStreaming: false });
  },
}));
