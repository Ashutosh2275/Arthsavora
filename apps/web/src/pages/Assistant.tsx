import React, { useEffect, useRef, useState } from 'react';
import {
  Bot,
  Send,
  Plus,
  Trash2,
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  CreditCard,
  PieChart,
  Calendar,
  AlertTriangle,
  RefreshCw,
  Sliders,
  DollarSign,
  Search,
} from 'lucide-react';
import type {
  AssistantActionDraft,
  AssistantConversation,
  AssistantMessage,
} from '@arthsavora/contracts';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useAssistantStore } from '@/store/useAssistantStore';

const SUGGESTED_PROMPTS = [
  {
    icon: DollarSign,
    category: 'Spending Overview',
    prompt: 'How much did I spend this month and where is most of my money going?',
  },
  {
    icon: PieChart,
    category: 'Category Deep-dive',
    prompt: 'How much did I spend on food and groceries last month?',
  },
  {
    icon: TrendingUp,
    category: 'Cash Flow & Forecast',
    prompt: 'What is my projected cash flow for the next 30 days?',
  },
  {
    icon: Calendar,
    category: 'Upcoming Commitments',
    prompt: 'What recurring payments and subscription renewals are due this week?',
  },
  {
    icon: AlertTriangle,
    category: 'Budget Health',
    prompt: 'Am I likely to exceed any of my monthly category budgets?',
  },
  {
    icon: Sliders,
    category: 'Action Proposal',
    prompt: 'Create a monthly budget for Food with a limit of ₹15,000.',
  },
];

export function Assistant() {
  const {
    conversations,
    activeConversation,
    messages,
    isLoading,
    isActionLoading,
    error,
    usage,
    fetchConversations,
    selectConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    confirmAction,
    cancelAction,
    fetchUsage,
  } = useAssistantStore();

  const [inputContent, setInputContent] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConversations();
    fetchUsage();
  }, [fetchConversations, fetchUsage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleCreateNew = async () => {
    try {
      await createConversation('New Financial Chat');
    } catch {
      // Handled in store
    }
  };

  const handleSelectConv = (id: string) => {
    if (activeConversation?.id !== id) {
      selectConversation(id);
    }
  };

  const handleDeleteConv = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(id);
    }
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || inputContent).trim();
    if (!text) return;

    setInputContent('');

    try {
      let targetConvId = activeConversation?.id;
      if (!targetConvId) {
        const newConv = await createConversation(text.slice(0, 30) + '...');
        targetConvId = newConv.id;
      }
      await sendMessage(targetConvId, text);
    } catch {
      // Handled in store
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleConfirmDraft = async (draft: AssistantActionDraft) => {
    try {
      await confirmAction(draft.id, draft.confirmation_token);
    } catch {
      // Handled in store
    }
  };

  const handleCancelDraft = async (draft: AssistantActionDraft) => {
    try {
      await cancelAction(draft.id);
    } catch {
      // Handled in store
    }
  };

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 overflow-hidden">
      {/* ----------------------------------------------------------------- */}
      {/* Sidebar: Conversation Threads */}
      {/* ----------------------------------------------------------------- */}
      <aside className="w-80 border-r border-slate-800 bg-slate-900/60 flex flex-col justify-between hidden md:flex">
        <div className="p-4 border-b border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bot className="w-5 h-5 text-emerald-400" />
              <h2 className="font-semibold text-sm tracking-wide uppercase text-slate-300">
                AI Assistant
              </h2>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCreateNew}
              className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
            >
              <Plus className="w-3.5 h-3.5 mr-1" /> New Chat
            </Button>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
            <Input
              type="text"
              placeholder="Search chats..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 text-xs bg-slate-950/50 border-slate-800 text-slate-200"
            />
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredConversations.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No conversations yet. Start a new one!
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isActive = activeConversation?.id === c.id;
              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectConv(c.id)}
                  className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-colors ${
                    isActive
                      ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                      : 'hover:bg-slate-800/60 text-slate-300 border border-transparent'
                  }`}
                >
                  <div className="truncate flex-1 pr-2">
                    <p className="font-medium truncate">{c.title}</p>
                    <span className="text-[10px] text-slate-500">
                      {new Date(c.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConv(e, c.id)}
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 text-slate-500 transition-opacity"
                    title="Delete Chat"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Usage Telemetry Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-400 space-y-1">
          <div className="flex justify-between">
            <span>Provider:</span>
            <span className="font-mono text-slate-300">
              {activeConversation?.model_provider || 'Mock / Deterministic'}
            </span>
          </div>
          {usage && (
            <div className="flex justify-between">
              <span>Tokens Used:</span>
              <span className="font-mono text-slate-300">
                {usage.total_tokens.toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </aside>

      {/* ----------------------------------------------------------------- */}
      {/* Main Chat Interface */}
      {/* ----------------------------------------------------------------- */}
      <main className="flex-1 flex flex-col justify-between overflow-hidden relative">
        {/* Top Header */}
        <header className="h-14 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/30">
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h1 className="font-semibold text-sm text-slate-100">
                {activeConversation?.title || 'Financial Intelligence Assistant'}
              </h1>
              <p className="text-[10px] text-slate-400">
                Institutional Financial Natural-Language Interface
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Badge variant="neutral" className="text-[10px] bg-slate-800 border-slate-700 text-slate-300">
              <ShieldCheck className="w-3 h-3 mr-1 text-emerald-400" /> Human Confirmation Required
            </Badge>
          </div>
        </header>

        {/* Message Feed / Landing Experience */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center justify-between">
              <span>{error}</span>
            </div>
          )}

          {(!activeConversation || messages.length === 0) ? (
            <div className="max-w-3xl mx-auto py-12 space-y-8">
              <div className="text-center space-y-3">
                <div className="inline-flex p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-2">
                  <Bot className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-100">
                  How can I help you understand your finances today?
                </h2>
                <p className="text-sm text-slate-400 max-w-lg mx-auto">
                  Ask questions about expenses, budgets, upcoming bills, or cash flow. The assistant synthesizes verified institutional records.
                </p>
              </div>

              {/* Prompt Suggestions Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-4">
                {SUGGESTED_PROMPTS.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(item.prompt)}
                      className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-slate-800/60 hover:border-slate-700 transition-all text-left flex items-start space-x-3 group"
                    >
                      <div className="p-2 rounded-lg bg-slate-800 text-emerald-400 group-hover:bg-emerald-500/20 group-hover:text-emerald-300 transition-colors">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                          {item.category}
                        </span>
                        <p className="text-xs text-slate-200 mt-0.5 line-clamp-2">
                          {item.prompt}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'} space-x-3`}
                  >
                    {!isUser && (
                      <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0 mt-1">
                        <Bot className="w-4 h-4 text-emerald-400" />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed space-y-3 ${
                        isUser
                          ? 'bg-emerald-600 text-white rounded-br-none shadow-md'
                          : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm'
                      }`}
                    >
                      {/* Assistant Header Metadata */}
                      {!isUser && msg.intent && (
                        <div className="flex items-center space-x-2 text-[10px] text-slate-400 pb-1 border-b border-slate-800/60">
                          <Badge variant="neutral" className="text-[9px] uppercase border-slate-700 text-slate-400">
                            {msg.intent.replace(/_/g, ' ')}
                          </Badge>
                          {msg.latency_ms > 0 && (
                            <span className="font-mono">{msg.latency_ms}ms</span>
                          )}
                        </div>
                      )}

                      {/* Content */}
                      <div className="whitespace-pre-wrap">{msg.content}</div>

                      {/* Tool Calls Execution Badges */}
                      {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/60 space-y-1">
                          <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
                            Verified Financial Services Called:
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.tool_calls.map((tc, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                              >
                                ⚡ {tc.tool_name || Object.keys(tc)[0] || 'service'}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Staged Action Proposal Card */}
                      {!isUser && msg.action_draft && (
                        <div className="mt-3 p-3.5 rounded-xl bg-slate-950/80 border border-amber-500/30 space-y-2.5">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wide flex items-center">
                              <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Action Proposal (Human Confirmation Required)
                            </span>
                            <Badge
                              variant="neutral"
                              className={`text-[9px] uppercase ${
                                msg.action_draft.status === 'confirmed'
                                  ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10'
                                  : msg.action_draft.status === 'cancelled'
                                  ? 'border-red-500 text-red-400 bg-red-500/10'
                                  : 'border-amber-500 text-amber-400 bg-amber-500/10'
                              }`}
                            >
                              {msg.action_draft.status}
                            </Badge>
                          </div>

                          <p className="text-xs font-medium text-slate-200">
                            {msg.action_draft.action_summary}
                          </p>

                          {msg.action_draft.status === 'pending' && (
                            <div className="flex items-center space-x-2 pt-1">
                              <Button
                                size="sm"
                                disabled={isActionLoading}
                                onClick={() => handleConfirmDraft(msg.action_draft!)}
                                className="h-7 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                              >
                                <CheckCircle2 className="w-3 h-3 mr-1" /> Confirm & Execute
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={isActionLoading}
                                onClick={() => handleCancelDraft(msg.action_draft!)}
                                className="h-7 text-xs border-slate-700 hover:bg-slate-800 text-slate-300"
                              >
                                <XCircle className="w-3 h-3 mr-1 text-slate-400" /> Cancel
                              </Button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0 animate-pulse">
                    <Bot className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400 rounded-bl-none flex items-center space-x-2">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                    <span>Analyzing financial records & synthesizing response...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/60">
          <div className="max-w-3xl mx-auto space-y-2">
            <div className="relative flex items-center">
              <Input
                type="text"
                placeholder="Ask anything about your spending, budgets, cash flow, or subscriptions..."
                value={inputContent}
                onChange={(e) => setInputContent(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                className="pr-12 text-xs bg-slate-950 border-slate-800 text-slate-100 placeholder:text-slate-500 h-11"
              />
              <Button
                size="sm"
                onClick={() => handleSend()}
                disabled={isLoading || !inputContent.trim()}
                className="absolute right-1.5 h-8 w-8 p-0 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            </div>
            <p className="text-[10px] text-center text-slate-500">
              ARTHSAVORA Financial Assistant is an informational tool. Ledger transactions and modifications require explicit user confirmation.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
