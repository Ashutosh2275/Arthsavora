import React, { useEffect, useState } from 'react';
import api from '../api/axios';
import { 
  Target, 
  TrendingUp, 
  Calendar, 
  ShieldCheck, 
  Plus, 
  Trash2, 
  Lightbulb, 
  AlertCircle,
  Clock
} from 'lucide-react';

export default function Goals() {
  const [goals, setGoals] = useState([]);
  const [insights, setInsights] = useState(null);
  const [newGoal, setNewGoal] = useState({ name: '', target_amount: '', current_amount: '', category: 'Savings' });
  const [loading, setLoading] = useState(true);

  useEffect(() => { 
    fetchAll(); 
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [gRes, iRes] = await Promise.all([
        api.get('/goals/'),
        api.get('/goals/insights')
      ]);
      setGoals(gRes.data);
      setInsights(iRes.data);
    } catch (err) {
      console.error("Failed to fetch goals data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddGoal = async (e) => {
    e.preventDefault();
    if (!newGoal.name || !newGoal.target_amount) return;

    try {
      await api.post('/goals/', { 
          ...newGoal, 
          target_amount: parseFloat(newGoal.target_amount),
          current_amount: parseFloat(newGoal.current_amount) || 0 
      });
      setNewGoal({ name: '', target_amount: '', current_amount: '', category: 'Savings' });
      fetchAll();
    } catch (err) {
      alert("Failed to add goal.");
    }
  };

  const deleteGoal = async (id) => {
    try {
      await api.delete(`/goals/${id}`);
      fetchAll();
    } catch (err) {
      alert("Failed to delete goal.");
    }
  };

  if (loading && goals.length === 0) {
    return (
      <div className="min-h-screen bg-[#0b0f1a] flex items-center justify-center">
        <div className="text-indigo-400 animate-pulse font-bold uppercase tracking-widest">Calculating Timelines...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white p-4 md:p-10">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10">
          <h2 className="text-3xl font-bold flex items-center gap-3">
            <Target className="text-indigo-400" /> Financial Milestones
          </h2>
          <p className="text-slate-500 mt-2">AI-driven predictions for your future wealth goals.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Form & Insights */}
          <div className="lg:col-span-1 space-y-6">
            <form onSubmit={handleAddGoal} className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2rem] shadow-xl">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-6 flex items-center gap-2">
                <Plus size={14} /> Create New Goal
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] font-bold text-slate-600 uppercase ml-1">Goal Name</label>
                  <input 
                    type="text" placeholder="e.g. Dream House" 
                    className="w-full bg-slate-950 border border-slate-800 p-3.5 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500 transition-all mt-1"
                    value={newGoal.name} onChange={e => setNewGoal({...newGoal, name: e.target.value})} required
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-600 uppercase ml-1">Target Amount (₹)</label>
                  <input 
                    type="number" placeholder="500000" 
                    className="w-full bg-slate-950 border border-slate-800 p-3.5 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500 transition-all mt-1 font-mono"
                    value={newGoal.target_amount} onChange={e => setNewGoal({...newGoal, target_amount: e.target.value})} required
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-600 uppercase ml-1">Already Saved (₹)</label>
                  <input 
                    type="number" placeholder="0" 
                    className="w-full bg-slate-950 border border-slate-800 p-3.5 rounded-2xl outline-none focus:ring-2 focus:ring-indigo-500 transition-all mt-1 font-mono"
                    value={newGoal.current_amount} onChange={e => setNewGoal({...newGoal, current_amount: e.target.value})}
                  />
                </div>
                <button className="w-full bg-indigo-600 hover:bg-indigo-500 py-4 rounded-2xl font-bold shadow-lg shadow-indigo-600/20 transition-all active:scale-95 mt-4">
                  Set Milestone
                </button>
              </div>
            </form>

            {insights && (
              <div className="bg-gradient-to-br from-indigo-900/20 to-slate-900 border border-indigo-500/20 p-8 rounded-[2rem]">
                <div className="flex items-center gap-2 text-indigo-400 font-bold text-[10px] uppercase tracking-widest mb-6">
                   <Lightbulb size={16} /> AI Investment Strategy
                </div>
                {insights.recommendations.map((rec, i) => (
                  <div key={i} className="space-y-4">
                    <div className="text-[10px] font-black text-white px-3 py-1 bg-indigo-600 w-fit rounded-full uppercase tracking-tighter">
                      {rec.type} Profile
                    </div>
                    <p className="text-slate-400 text-sm leading-relaxed italic">"{rec.text}"</p>
                    <div className="pt-4 border-t border-slate-800">
                       <p className="text-[10px] text-slate-600 font-bold uppercase">Estimated Monthly Surplus</p>
                       <p className="text-xl font-mono font-bold text-emerald-400">₹{insights.surplus.toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Goals Progress Grid */}
          <div className="lg:col-span-2 space-y-6">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 px-2">Active Milestones</h3>
            
            {goals.map((goal) => {
              const progress = Math.min(100, (goal.current_amount / goal.target_amount) * 100);
              return (
                <div key={goal.id} className="bg-slate-900/40 border border-slate-800/60 p-8 rounded-[2.5rem] hover:border-indigo-500/40 transition-all group backdrop-blur-sm">
                  <div className="flex justify-between items-start mb-6">
                    <div className="flex gap-4 items-center">
                      <div className={`p-4 rounded-2xl ${goal.is_on_track ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                        <ShieldCheck size={24} />
                      </div>
                      <div>
                        <h4 className="text-2xl font-bold group-hover:text-indigo-400 transition-colors">{goal.name}</h4>
                        <div className="flex gap-4 mt-1 text-[10px] font-black uppercase tracking-widest">
                          <span className="text-slate-500">Target: ₹{goal.target_amount.toLocaleString()}</span>
                          <span className={goal.is_on_track ? 'text-emerald-500' : 'text-amber-500'}>
                            {goal.is_on_track ? 'On Track' : 'Falling Behind'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button 
                      onClick={() => deleteGoal(goal.id)} 
                      className="text-slate-800 hover:text-red-500 p-2 transition-all hover:bg-red-500/10 rounded-xl"
                    >
                        <Trash2 size={20} />
                    </button>
                  </div>

                  {/* High-End Progress Bar */}
                  <div className="relative pt-2">
                    <div className="flex mb-2 items-center justify-between">
                      <div>
                        <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-indigo-400 bg-indigo-400/10">
                          Progress
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-mono font-bold inline-block text-indigo-400">
                          {progress.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div className="overflow-hidden h-3 mb-4 text-xs flex rounded-full bg-slate-800">
                      <div 
                        style={{ width: `${progress}%` }} 
                        className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-indigo-500 transition-all duration-1000"
                      ></div>
                    </div>
                  </div>

                  <div className="flex flex-col md:flex-row justify-between items-center gap-4 mt-6 pt-6 border-t border-slate-800/50">
                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                      <Clock size={16} className="text-indigo-500" /> 
                      AI Prediction: <span className="text-white font-bold">{goal.predicted_completion_date}</span>
                    </div>
                    <div className="text-xs text-slate-600 font-bold bg-slate-950 px-4 py-2 rounded-full border border-slate-800">
                       Remaining: ₹{(goal.target_amount - goal.current_amount).toLocaleString()}
                    </div>
                  </div>
                </div>
              );
            })}
            
            {goals.length === 0 && (
              <div className="text-center py-32 bg-slate-900/10 rounded-[3rem] border-2 border-dashed border-slate-800/40">
                <Target size={48} className="mx-auto text-slate-800 mb-4" />
                <p className="text-slate-600 font-medium">Your financial horizon is empty. Define your first milestone to begin tracking.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}