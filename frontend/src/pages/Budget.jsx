import React, { useEffect, useState } from 'react';
import api from '../api/axios';
import { Target, TrendingUp, AlertCircle, Sparkles } from 'lucide-react';

export default function Budget() {
  const [budgets, setBudgets] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [newBudget, setNewBudget] = useState({ category: 'Food', limit: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const [bRes, fRes] = await Promise.all([
      api.get('/budget/status'),
      api.get('/budget/forecast')
    ]);
    setBudgets(bRes.data);
    setForecast(fRes.data);
  };

  const handleSetBudget = async (e) => {
    e.preventDefault();
    await api.post('/budget/', { ...newBudget, limit: parseFloat(newBudget.limit) });
    setNewBudget({ category: 'Food', limit: '' });
    fetchData();
  };

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white p-4 md:p-10">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold mb-8 flex items-center gap-3">
          <Target className="text-indigo-400" /> Budgeting & AI Forecast
        </h2>

        {/* AI Forecast Card */}
        <div className="bg-gradient-to-br from-indigo-900/40 to-slate-900 border border-indigo-500/30 p-8 rounded-[2rem] mb-10">
          <div className="flex items-center gap-2 mb-4 text-indigo-300 font-bold uppercase tracking-widest text-xs">
            <Sparkles size={16} /> AI Prediction for Next Month
          </div>
          <div className="flex items-end gap-4">
            <h3 className="text-5xl font-mono font-bold text-white">
              ₹{forecast?.prediction?.toLocaleString() || '0.00'}
            </h3>
            <span className="text-slate-500 mb-2 text-sm italic font-medium">
              Based on your {forecast?.status}
            </span>
          </div>
          <p className="text-slate-400 mt-4 text-sm max-w-md leading-relaxed">
            Our ARIMA model analyzed your spending velocity. We expect your expenses to hit this amount next month if your habits continue.
          </p>
        </div>

        {/* Set Budget Form */}
        <form onSubmit={handleSetBudget} className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl mb-10 flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest ml-1">Category</label>
            <select 
              value={newBudget.category}
              onChange={(e) => setNewBudget({...newBudget, category: e.target.value})}
              className="w-full bg-slate-800 border border-slate-700 p-3 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option>Food</option><option>Travel</option><option>Shopping</option><option>Bills</option><option>Entertainment</option>
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest ml-1">Monthly Limit (₹)</label>
            <input 
              type="number" 
              value={newBudget.limit}
              onChange={(e) => setNewBudget({...newBudget, limit: e.target.value})}
              className="w-full bg-slate-800 border border-slate-700 p-3 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="5000" required
            />
          </div>
          <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-8 py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-600/20">
            Set Limit
          </button>
        </form>

        {/* Budget Progress Bars */}
        <div className="grid gap-6">
          {budgets.map((b) => (
            <div key={b.category} className="bg-slate-900/30 border border-slate-800/50 p-6 rounded-3xl">
              <div className="flex justify-between items-center mb-4">
                <h4 className="font-bold text-lg">{b.category}</h4>
                <span className="text-sm font-bold text-slate-400">
                  ₹{b.spent.toLocaleString()} / <span className="text-indigo-400">₹{b.limit.toLocaleString()}</span>
                </span>
              </div>
              <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 ${b.percent > 90 ? 'bg-red-500' : 'bg-indigo-500'}`} 
                  style={{ width: `${b.percent}%` }}
                ></div>
              </div>
              <div className="flex justify-between mt-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                <span>{b.percent.toFixed(0)}% Consumed</span>
                <span>₹{b.remaining.toLocaleString()} Left</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}