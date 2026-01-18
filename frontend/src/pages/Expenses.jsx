import React, { useEffect, useState } from 'react';
import useExpenseStore from '../store/useExpenseStore';
import api from '../api/axios';
import { 
  Plus, Trash2, Wallet, Calendar, Tag, Zap, Sparkles, 
  Utensils, Plane, ShoppingBag, Receipt, Camera, Loader2 
} from 'lucide-react';

export default function Expenses() {
  const { expenses, fetchExpenses, addExpense, deleteExpense, parseSMS } = useExpenseStore();
  const [form, setForm] = useState({ amount: '', description: '', category: 'Shopping' });
  const [showAI, setShowAI] = useState(false);
  const [smsInput, setSmsInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => { fetchExpenses(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount || !form.description) return;
    const res = await addExpense({ ...form, amount: parseFloat(form.amount) });
    if (res.success) setForm({ amount: '', description: '', category: 'Shopping' });
  };

  const handleAIParsing = async () => {
    setIsProcessing(true);
    const res = await parseSMS(smsInput);
    if (res.success) {
      setForm({ amount: res.data.amount, description: res.data.description, category: res.data.category });
      setShowAI(false);
      setSmsInput("");
    }
    setIsProcessing(false);
  };

  const handleOCRScan = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post('/ml/scan-receipt', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setForm({ amount: res.data.amount, description: res.data.description, category: res.data.category });
      setShowAI(false);
    } catch (err) {
      alert("OCR Scan failed. Check if Tesseract is installed on your PC.");
    } finally {
      setIsProcessing(false);
    }
  };

  const getCategoryStyles = (cat) => {
    switch (cat) {
      case 'Food': return { bg: 'bg-orange-500/10', text: 'text-orange-400', icon: <Utensils size={14}/> };
      case 'Travel': return { bg: 'bg-blue-500/10', text: 'text-blue-400', icon: <Plane size={14}/> };
      case 'Shopping': return { bg: 'bg-emerald-500/10', text: 'text-emerald-400', icon: <ShoppingBag size={14}/> };
      case 'Bills': return { bg: 'bg-red-500/10', text: 'text-red-400', icon: <Receipt size={14}/> };
      default: return { bg: 'bg-slate-800', text: 'text-slate-400', icon: <Tag size={14}/> };
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white">
      <header className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold flex items-center gap-3">
          <Wallet className="text-indigo-400" /> Expense Management
        </h2>
        <button 
          onClick={() => setShowAI(!showAI)}
          className="flex items-center gap-2 bg-indigo-600/20 text-indigo-400 px-6 py-3 rounded-2xl border border-indigo-500/30 font-bold transition-all hover:bg-indigo-600/30 shadow-lg"
        >
          <Sparkles size={18} /> AI Smart Import
        </button>
      </header>

      {showAI && (
        <div className="mb-10 p-10 bg-slate-900/50 border border-indigo-500/20 rounded-[2.5rem] shadow-2xl animate-in zoom-in-95 duration-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div className="space-y-4 border-r border-slate-800/50 pr-10">
              <div className="flex items-center gap-2 text-indigo-400 font-black text-[10px] uppercase tracking-widest mb-2"><Zap size={14} fill="currentColor"/> SMS Parser</div>
              <textarea 
                className="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                placeholder="Paste bank SMS here... e.g. 'Amt Sent Rs.500 to Swiggy'"
                rows="4" value={smsInput} onChange={(e) => setSmsInput(e.target.value)}
              />
              <button onClick={handleAIParsing} disabled={isProcessing} className="w-full bg-indigo-600 hover:bg-indigo-500 py-4 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20">
                {isProcessing ? <Loader2 className="animate-spin"/> : "Execute Magic Parse"}
              </button>
            </div>
            <div className="flex flex-col justify-center items-center text-center">
              <div className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-6"><Camera size={14} className="inline mr-2"/> Receipt Vision (OCR)</div>
              <label className="w-full h-48 border-2 border-dashed border-slate-800 rounded-3xl flex flex-col items-center justify-center cursor-pointer hover:border-indigo-500/50 transition-all bg-slate-950 group">
                <Camera size={48} className="text-slate-700 group-hover:text-indigo-500 transition-all mb-4"/>
                <span className="text-xs text-slate-500 font-bold">Upload Bill Image</span>
                <input type="file" className="hidden" accept="image/*" onChange={handleOCRScan} />
              </label>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 p-8 rounded-[2rem] mb-12 grid grid-cols-1 md:grid-cols-4 gap-6 items-end shadow-xl">
        <div className="space-y-2">
          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Amount</label>
          <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({...form, amount: e.target.value})} className="w-full bg-slate-800 border border-slate-700 p-4 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-lg" placeholder="0.00" required />
        </div>
        <div className="md:col-span-2 space-y-2">
          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Description</label>
          <input type="text" value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} className="w-full bg-slate-800 border border-slate-700 p-4 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Store or Merchant Name" required />
        </div>
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-2xl shadow-lg shadow-indigo-600/20 transition-all active:scale-95">Save Transaction</button>
      </form>

      <div className="space-y-4">
        {expenses.map((expense) => {
          const style = getCategoryStyles(expense.category);
          return (
            <div key={expense._id} className="bg-slate-900/30 border border-slate-800/40 p-6 rounded-[2rem] flex items-center justify-between group hover:border-indigo-500/30 transition-all">
              <div className="flex items-center gap-6">
                <div className={`${style.bg} ${style.text} p-5 rounded-[1.2rem] transition-transform group-hover:rotate-6`}>{style.icon}</div>
                <div>
                  <h4 className="font-bold text-slate-200 text-lg capitalize">{expense.description}</h4>
                  <div className="flex items-center gap-4 text-xs mt-2 text-slate-500 font-medium">
                    <span><Calendar size={14} className="inline mr-1 text-indigo-500"/> {new Date(expense.date).toLocaleDateString()}</span>
                    <span className={`${style.bg} ${style.text} px-3 py-1 rounded-full font-black uppercase tracking-tighter text-[10px]`}>{expense.category}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-8">
                <span className="text-2xl font-mono font-bold text-indigo-400">₹{parseFloat(expense.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                <button onClick={() => deleteExpense(expense._id)} className="text-slate-800 hover:text-red-500 transition-all bg-slate-900/50 p-2 rounded-xl"><Trash2 size={20} /></button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}