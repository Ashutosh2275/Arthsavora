import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Assistant } from '../Assistant';
import { useAssistantStore } from '@/store/useAssistantStore';

vi.mock('@/store/useAssistantStore');

const mockConversation = {
  id: 'conv-1',
  workspace_id: 'ws-1',
  user_id: 'user-1',
  title: 'Monthly Spending Breakdown',
  status: 'active',
  model_provider: 'mock',
  model_name: 'mock-fin-v1',
  message_count: 2,
  created_at: '2026-11-14T08:00:00Z',
  updated_at: '2026-11-14T08:05:00Z',
};

const mockMessages = [
  {
    id: 'msg-1',
    conversation_id: 'conv-1',
    workspace_id: 'ws-1',
    role: 'user',
    content: 'How much did I spend this month?',
    tool_calls: [],
    tool_results: [],
    structured_data: {},
    action_draft: null,
    tokens_prompt: 15,
    tokens_completion: 0,
    latency_ms: 0,
    created_at: '2026-11-14T08:00:00Z',
  },
  {
    id: 'msg-2',
    conversation_id: 'conv-1',
    workspace_id: 'ws-1',
    role: 'assistant',
    content: 'You spent a total of ₹42,500.00 across 18 transactions this month.',
    intent: 'expense_summary',
    tool_calls: [{ tool_name: 'get_expense_summary', arguments: {} }],
    tool_results: [{ tool_name: 'get_expense_summary', status: 'success' }],
    structured_data: {},
    action_draft: null,
    tokens_prompt: 120,
    tokens_completion: 45,
    latency_ms: 180,
    created_at: '2026-11-14T08:00:05Z',
  },
];

const mockDraftMessage = {
  id: 'msg-3',
  conversation_id: 'conv-1',
  workspace_id: 'ws-1',
  role: 'assistant',
  content: 'I have prepared a draft budget for Food with a monthly limit of ₹15,000.',
  intent: 'action_draft',
  tool_calls: [{ tool_name: 'create_budget_draft', arguments: {} }],
  tool_results: [],
  structured_data: {},
  action_draft: {
    id: 'draft-1',
    conversation_id: 'conv-1',
    workspace_id: 'ws-1',
    action_type: 'create_budget',
    action_summary: 'Create Monthly Budget: ₹15,000 for Food',
    parameters: { name: 'Food Budget', amount: 15000 },
    status: 'pending',
    confirmation_token: 'token-abc-123',
    expires_at: '2026-11-15T08:00:00Z',
    created_at: '2026-11-14T08:00:10Z',
  },
  tokens_prompt: 100,
  tokens_completion: 40,
  latency_ms: 150,
  created_at: '2026-11-14T08:00:10Z',
};

const mockUsage = {
  total_requests: 12,
  total_tokens: 3450,
  tokens_prompt: 2400,
  tokens_completion: 1050,
  estimated_cost_usd: 0.0069,
  avg_latency_ms: 220,
};

describe('Assistant Component', () => {
  let fetchConversationsMock: any;
  let selectConversationMock: any;
  let createConversationMock: any;
  let deleteConversationMock: any;
  let sendMessageMock: any;
  let confirmActionMock: any;
  let cancelActionMock: any;
  let fetchUsageMock: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock scrollIntoView
    window.HTMLElement.prototype.scrollIntoView = vi.fn();

    fetchConversationsMock = vi.fn();
    selectConversationMock = vi.fn();
    createConversationMock = vi.fn().mockResolvedValue({ id: 'conv-new', title: 'New Financial Chat' });
    deleteConversationMock = vi.fn();
    sendMessageMock = vi.fn().mockResolvedValue(mockMessages[1]);
    confirmActionMock = vi.fn().mockResolvedValue({ status: 'confirmed' });
    cancelActionMock = vi.fn().mockResolvedValue({});
    fetchUsageMock = vi.fn();

    (useAssistantStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      conversations: [mockConversation],
      activeConversation: mockConversation,
      messages: mockMessages,
      isLoading: false,
      isActionLoading: false,
      error: null,
      usage: mockUsage,
      fetchConversations: fetchConversationsMock,
      selectConversation: selectConversationMock,
      createConversation: createConversationMock,
      deleteConversation: deleteConversationMock,
      sendMessage: sendMessageMock,
      confirmAction: confirmActionMock,
      cancelAction: cancelActionMock,
      fetchUsage: fetchUsageMock,
    });
  });

  it('renders conversations sidebar and message feed', () => {
    render(<Assistant />);

    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getAllByText('Monthly Spending Breakdown').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('How much did I spend this month?')).toBeInTheDocument();
    expect(
      screen.getByText('You spent a total of ₹42,500.00 across 18 transactions this month.')
    ).toBeInTheDocument();
    expect(screen.getByText(/expense summary/i)).toBeInTheDocument();
    expect(screen.getByText(/⚡ get_expense_summary/i)).toBeInTheDocument();
  });

  it('renders landing state when no active conversation or messages exist', () => {
    (useAssistantStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      conversations: [],
      activeConversation: null,
      messages: [],
      isLoading: false,
      isActionLoading: false,
      error: null,
      usage: null,
      fetchConversations: fetchConversationsMock,
      selectConversation: selectConversationMock,
      createConversation: createConversationMock,
      deleteConversation: deleteConversationMock,
      sendMessage: sendMessageMock,
      confirmAction: confirmActionMock,
      cancelAction: cancelActionMock,
      fetchUsage: fetchUsageMock,
    });

    render(<Assistant />);

    expect(
      screen.getByText(/How can I help you understand your finances today\?/i)
    ).toBeInTheDocument();
    expect(screen.getByText('Spending Overview')).toBeInTheDocument();
    expect(screen.getByText('Cash Flow & Forecast')).toBeInTheDocument();
    expect(screen.getByText('Action Proposal')).toBeInTheDocument();
  });

  it('allows user to send a new message via input field', async () => {
    render(<Assistant />);

    const input = screen.getByPlaceholderText(
      /Ask anything about your spending, budgets, cash flow, or subscriptions.../i
    );
    fireEvent.change(input, { target: { value: 'Where is my money going?' } });

    const sendBtn = screen.getByRole('button', { name: '' }); // Send icon button
    fireEvent.click(sendBtn);

    expect(sendMessageMock).toHaveBeenCalledWith('conv-1', 'Where is my money going?');
  });

  it('renders Action Proposal Card with Confirm and Cancel buttons', () => {
    (useAssistantStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      conversations: [mockConversation],
      activeConversation: mockConversation,
      messages: [...mockMessages, mockDraftMessage],
      isLoading: false,
      isActionLoading: false,
      error: null,
      usage: mockUsage,
      fetchConversations: fetchConversationsMock,
      selectConversation: selectConversationMock,
      createConversation: createConversationMock,
      deleteConversation: deleteConversationMock,
      sendMessage: sendMessageMock,
      confirmAction: confirmActionMock,
      cancelAction: cancelActionMock,
      fetchUsage: fetchUsageMock,
    });

    render(<Assistant />);

    expect(
      screen.getByText(/Action Proposal \(Human Confirmation Required\)/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText('Create Monthly Budget: ₹15,000 for Food')
    ).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute/i });
    expect(confirmBtn).toBeInTheDocument();
    fireEvent.click(confirmBtn);
    expect(confirmActionMock).toHaveBeenCalledWith('draft-1', 'token-abc-123');

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    expect(cancelBtn).toBeInTheDocument();
    fireEvent.click(cancelBtn);
    expect(cancelActionMock).toHaveBeenCalledWith('draft-1');
  });

  it('allows creating a new chat from the sidebar button', () => {
    render(<Assistant />);

    const newChatBtn = screen.getByRole('button', { name: /New Chat/i });
    fireEvent.click(newChatBtn);

    expect(createConversationMock).toHaveBeenCalledWith('New Financial Chat');
  });
});
