import React, { useEffect, useState } from 'react';
import api from '../api/axios';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend 
} from 'recharts';
import { TrendingUp, Activity, PieChart as PieIcon, ShieldAlert } from 'lucide-react';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/analytics/summary').then(res => {
      setData(res.data);
      setLoading(false);
    });
  }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-indigo-400 animate-pulse font-bold tracking-widest uppercase text-sm">Initializing AI Analytics...</div>
    </div>
  );

  return (
    <div className="space-y-10">
      <header>
        <h2 className="text-3xl font-bold flex items-center gap-3">
          <Activity className="text-indigo-400" /> Financial Intelligence
        </h2>
        <p className="text-slate-500 mt-2">Real-time spending analysis and AI outlier detection.</p>
      </header>

      {/* Phase 8: AI Risk Alerts */}
      {data.anomalies && data.anomalies.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-[2rem] flex flex-col md:flex-row items-center gap-6 animate-in slide-in-from-top-4">
          <div className="bg-red-500 p-4 rounded-2xl shadow-lg shadow-red-500/20">
            <ShieldAlert size={32} className="text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold text-red-400">Suspicious Activity Detected</h3>
            <p className="text-slate-400 text-sm mt-1">Our Isolation Forest model flagged {data.anomalies.length} transaction(s) as statistical outliers.</p>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2 w-full md:w-auto">
            {data.anomalies.map((anomaly, idx) => (
              <div key={idx} className="bg-slate-900 border border-red-500/30 p-4 rounded-2xl min-w-[200px]">
                <div className="text-[10px] font-bold text-red-500 uppercase tracking-tighter mb-1">Flagged Outlier</div>
                <div className="font-bold truncate text-sm">{anomaly.description}</div>
                <div className="text-lg font-mono font-black text-white">₹{anomaly.amount.toLocaleString()}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2rem] hover:border-indigo-500/30 transition-all">
          <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] mb-3">Monthly Outflow</p>
          <h3 className="text-4xl font-mono font-bold text-white">₹{data.totalSpent.toLocaleString()}</h3>
          <div className="mt-6 flex items-center gap-2 text-emerald-400 text-xs font-bold bg-emerald-400/10 w-fit px-3 py-1 rounded-full">
            <TrendingUp size={14} /> Normal Variance
          </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2rem] hover:border-indigo-500/30 transition-all">
          <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] mb-3">Daily Burn Rate</p>
          <h3 className="text-4xl font-mono font-bold text-indigo-400">₹{data.avgDaily.toLocaleString()}</h3>
          <p className="text-slate-600 text-[10px] mt-6 font-bold uppercase tracking-widest italic">Updated Real-time</p>
        </div>
        <div className="bg-indigo-600 p-8 rounded-[2rem] shadow-xl shadow-indigo-600/20 relative overflow-hidden">
          <p className="text-indigo-100/60 text-[10px] font-black uppercase tracking-[0.2em] mb-3">Platform Health</p>
          <h3 className="text-2xl font-bold text-white leading-tight">AI Models<br />Active & Optimal</h3>
          <Activity className="absolute bottom-[-10px] right-[-10px] text-white/5 w-32 h-32" />
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2.5rem]">
          <h4 className="text-sm font-black text-slate-400 mb-8 uppercase tracking-[0.25em] flex items-center gap-2">
            <TrendingUp className="text-indigo-400" size={16} /> Spending Velocity
          </h4>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.trendData}>
                <defs>
                  <linearGradient id="colorAmt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="date" stroke="#475569" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                <YAxis stroke="#475569" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '16px' }} />
                <Area type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={4} fillOpacity={1} fill="url(#colorAmt)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2.5rem]">
          <h4 className="text-sm font-black text-slate-400 mb-8 uppercase tracking-[0.25em] flex items-center gap-2">
            <PieIcon className="text-indigo-400" size={16} /> Portfolio Breakdown
          </h4>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.categoryData} innerRadius={70} outerRadius={90} paddingAngle={8} dataKey="value" stroke="none">
                  {data.categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} cornerRadius={10} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '16px' }} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}