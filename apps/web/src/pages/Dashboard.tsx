import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { TrendingUp, Activity, PieChart as PieIcon, ShieldAlert } from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { AnalyticsSummaryResponse } from '@arthsavora/contracts';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#ec4899'];

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<AnalyticsSummaryResponse>('/analytics/summary')
      .then((res) => {
        setData(res.data);
      })
      .catch((err) => {
        console.error('Failed to load dashboard summary:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Skeleton className="h-80 rounded-2xl" />
          <Skeleton className="h-80 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-96 items-center justify-center text-center">
        <p className="text-sm text-slate-400">Unable to load financial analytics.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Activity className="text-indigo-400" size={24} /> Financial Intelligence
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Real-time cash flow overview, category distribution, and risk alerts.
        </p>
      </header>

      {/* Anomaly / Risk Alert */}
      {data.anomalies && data.anomalies.length > 0 && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-5 flex flex-col md:flex-row items-start md:items-center gap-5">
          <div className="rounded-xl bg-rose-500 p-3 text-white shadow-md shadow-rose-500/20 shrink-0">
            <ShieldAlert size={24} />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-bold text-rose-300">Statistical Outliers Flagged</h4>
            <p className="text-xs text-slate-300 mt-0.5">
              Isolation Forest detected {data.anomalies.length} transaction(s) deviating from historical baselines.
            </p>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1 w-full md:w-auto">
            {data.anomalies.map((anomaly, idx) => (
              <div key={idx} className="rounded-xl border border-rose-500/30 bg-slate-900/90 p-3 min-w-[180px]">
                <div className="text-[10px] font-bold text-rose-400 uppercase tracking-wider mb-0.5">Outlier</div>
                <div className="font-semibold truncate text-xs text-white">{anomaly.description}</div>
                <div className="font-mono font-bold text-sm text-rose-300 mt-1">
                  {formatINR(anomaly.amount)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2">Monthly Outflow</p>
          <h3 className="text-3xl font-mono font-bold text-white tracking-tight">
            {formatINR(data.totalSpent)}
          </h3>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <TrendingUp size={14} /> Active Period
          </div>
        </Card>

        <Card>
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2">Daily Burn Rate</p>
          <h3 className="text-3xl font-mono font-bold text-indigo-400 tracking-tight">
            {formatINR(data.avgDaily)}
          </h3>
          <p className="text-[10px] font-medium text-slate-500 mt-4 uppercase tracking-wider">Computed Daily Average</p>
        </Card>

        <Card className="bg-indigo-600/10 border-indigo-500/30">
          <p className="text-[10px] font-black uppercase tracking-wider text-indigo-300 mb-2">Engine Status</p>
          <h3 className="text-xl font-bold text-white leading-snug">
            Financial Ledger & AI Services Active
          </h3>
          <p className="text-[10px] font-medium text-indigo-200/80 mt-4 uppercase tracking-wider">System Operational</p>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-6 flex items-center gap-2">
            <TrendingUp className="text-indigo-400" size={16} /> 30-Day Spending Velocity
          </h4>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.trendData}>
                <defs>
                  <linearGradient id="colorAmt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickMargin={8} axisLine={false} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickMargin={8} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                  formatter={(val: unknown) => [formatINR(val as number), 'Amount']}
                />
                <Area type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorAmt)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-6 flex items-center gap-2">
            <PieIcon className="text-indigo-400" size={16} /> Category Breakdown
          </h4>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.categoryData} innerRadius={65} outerRadius={88} paddingAngle={6} dataKey="value" stroke="none">
                  {data.categoryData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                  formatter={(val: unknown) => [formatINR(val as number), 'Spent']}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
