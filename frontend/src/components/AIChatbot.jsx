import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, Sparkles, User } from 'lucide-react';
import api from '../api/axios';

export default function AIChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hi! I am your Arthsavora Assistant. Ask me about your spending or goals!' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await api.post('/ml/chat', { message: userText });
      setMessages(prev => [...prev, { role: 'bot', text: res.data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: "I'm having trouble connecting to my brain. Check your API key." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-[100]">
      {isOpen ? (
        <div className="bg-slate-900 border border-indigo-500/30 w-80 md:w-96 h-[500px] rounded-[2.5rem] shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-6 duration-300">
          <div className="bg-indigo-600 p-5 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="bg-white/20 p-2 rounded-xl"><Bot size={20} className="text-white"/></div>
              <span className="font-black text-white text-xs uppercase tracking-widest">Arthsavora AI</span>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-white/60 hover:text-white"><X size={20}/></button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${
                  m.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-800 text-slate-300 rounded-tl-none'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && <div className="text-indigo-400 text-[10px] font-bold animate-pulse flex items-center gap-2"><Sparkles size={12}/> AI IS THINKING...</div>}
            <div ref={chatEndRef} />
          </div>

          <div className="p-4 bg-slate-950/50 border-t border-slate-800 flex gap-2">
            <input 
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about your budget..."
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-xs outline-none focus:border-indigo-500 text-white"
            />
            <button onClick={handleSend} className="bg-indigo-600 p-2.5 rounded-xl text-white hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-600/20">
              <Send size={16} />
            </button>
          </div>
        </div>
      ) : (
        <button 
          onClick={() => setIsOpen(true)}
          className="bg-indigo-600 hover:bg-indigo-500 w-16 h-16 rounded-full flex items-center justify-center shadow-2xl shadow-indigo-600/40 transition-all hover:scale-110 active:scale-90 animate-bounce-slow"
        >
          <MessageSquare className="text-white" size={28} />
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[#0b0f1a]"></div>
        </button>
      )}
    </div>
  );
}