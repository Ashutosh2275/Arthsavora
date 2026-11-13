import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, Sparkles } from 'lucide-react';
import api from '@/lib/axios';

interface Message {
  role: 'bot' | 'user';
  text: string;
}

export default function AIChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'bot',
      text: 'Hi! I am your Arthsavora Assistant. Ask me about your spending trends, category distributions, or savings goals.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userText = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await api.post<{ reply: string }>('/ml/chat', { message: userText });
      setMessages((prev) => [...prev, { role: 'bot', text: res.data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: 'The AI assistant is temporarily unavailable. Please verify API configuration.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {isOpen ? (
        <div className="flex h-[480px] w-80 md:w-96 flex-col overflow-hidden rounded-2xl border border-indigo-500/20 bg-slate-900 shadow-2xl animate-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center justify-between bg-indigo-600 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-white/20 p-1.5 text-white">
                <Bot size={18} />
              </div>
              <span className="text-xs font-black uppercase tracking-widest text-white">
                Arthsavora AI
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/70 hover:text-white"
            >
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-xs">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-tr-none'
                      : 'bg-slate-800 text-slate-200 rounded-tl-none border border-slate-700/50'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-[11px] font-bold text-indigo-400">
                <Sparkles size={12} className="animate-spin" />
                <span>Thinking...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="flex gap-2 border-t border-slate-800 bg-slate-950/70 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about your finances..."
              className="flex-1 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs text-white outline-none focus:border-indigo-500"
            />
            <button
              onClick={handleSend}
              disabled={loading}
              className="rounded-xl bg-indigo-600 px-3 py-2 text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-600 text-white shadow-xl shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95"
          aria-label="Open AI Assistant"
        >
          <MessageSquare size={24} />
          <span className="absolute -top-1 -right-1 h-3.5 w-3.5 rounded-full border-2 border-[#0b0f1a] bg-emerald-500" />
        </button>
      )}
    </div>
  );
}
