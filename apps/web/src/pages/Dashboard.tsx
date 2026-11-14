import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  Line,
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
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  Calendar,
  CreditCard,
  Download,
  Filter,
  HelpCircle,
  Info,
  Layers,
  PieChart as PieIcon,
  PiggyBank,
  RefreshCw,
  ShieldCheck,
  Tag,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import type { PeriodGrouping, ReportType } from '@arthsavora/contracts';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useAccountStore } from '@/store/useAccountStore';
import { type DatePreset, useAnalyticsStore } from '@/store/useAnalyticsStore';

const CATEGORY_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
  '#06b6d4', '#f97316', '#14b8a6', '#84cc16', '#64748b',
];

export default function Dashboard() {
  const {
    overview,
    cashFlow,
    categorySpending,
    merchantSpending,
    netWorth,
    comparison,
    loading,
    error,
    datePreset,
    startDate,
    endDate,
    grouping,
    selectedAccountId,
    setDatePreset,
    setCustomDateRange,
    setGrouping,
    setSelectedAccountId,
    fetchAnalytics,
    exportCSV,
  } = useAnalyticsStore();

  const { accounts, fetchAccounts } = useAccountStore();
  const [customStart, setCustomStart] = useState(startDate);
  const [customEnd, setCustomEnd] = useState(endDate);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchAccounts();
    fetchAnalytics();
  }, [fetchAccounts, fetchAnalytics]);

  const handleExport = async (type: ReportType) => {
    setExporting(true);
    const blob = await exportCSV(type);
    if (blob) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `arthsavora_${type}_${startDate}_${endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }
    setExporting(false);
  };

  const handleApplyCustomDates = (e: React.FormEvent) => {
    e.preventDefault();
    if (customStart && customEnd) {
      setCustomDateRange(customStart, customEnd);
    }
  };

  if (loading && !overview) {
    return (
      <div className="space-y-8 p-1">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Activity className="text-indigo-400" size={26} /> Financial Analytics & Insights
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative financial metrics and cash flow performance derived directly from verified records.
          </p>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAnalytics()}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-slate-300"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </Button>

          <div className="relative group">
            <Button
              variant="outline"
              size="sm"
              disabled={exporting}
              className="flex items-center gap-1.5 text-xs text-slate-300"
            >
              <Download size={14} /> Export CSV
            </Button>
            <div className="absolute right-0 top-full mt-1 hidden group-hover:block z-50 bg-slate-900 border border-slate-800 rounded-xl shadow-xl py-1 min-w-[160px]">
              <button
                onClick={() => handleExport('overview')}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                Summary Overview
              </button>
              <button
                onClick={() => handleExport('cash_flow')}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                Cash Flow Trends
              </button>
              <button
                onClick={() => handleExport('categories')}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                Category Spending
              </button>
              <button
                onClick={() => handleExport('merchants')}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                Top Merchants
              </button>
              <button
                onClick={() => handleExport('net_worth')}
                className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                Balance Sheet Position
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <Card className="bg-slate-900/40 border-slate-800/80 p-4">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
              <Calendar size={13} /> Period:
            </span>
            {(
              [
                ['this_month', 'This Month'],
                ['last_month', 'Last Month'],
                ['this_quarter', 'This Quarter'],
                ['current_fy', 'Current FY (India)'],
                ['last_30_days', 'Last 30 Days'],
                ['last_90_days', 'Last 90 Days'],
                ['custom', 'Custom'],
              ] as [DatePreset, string][]
            ).map(([presetKey, label]) => (
              <button
                key={presetKey}
                onClick={() => setDatePreset(presetKey)}
                className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
                  datePreset === presetKey
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Account Filter & Grouping Selectors */}
          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            {/* Account Selector */}
            <div className="flex items-center gap-1.5 text-xs">
              <Building2 size={13} className="text-slate-400" />
              <select
                aria-label="Filter by Financial Account"
                value={selectedAccountId || ''}
                onChange={(e) => setSelectedAccountId(e.target.value || null)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Accounts</option>
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.account_type})
                  </option>
                ))}
              </select>
            </div>

            {/* Interval Grouping */}
            <div className="flex items-center gap-1.5 text-xs">
              <Layers size={13} className="text-slate-400" />
              <select
                aria-label="Temporal Interval Grouping"
                value={grouping}
                onChange={(e) => setGrouping(e.target.value as PeriodGrouping)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="day">Daily</option>
                <option value="week">Weekly</option>
                <option value="month">Monthly</option>
                <option value="quarter">Quarterly</option>
                <option value="financial_year">Financial Year</option>
              </select>
            </div>
          </div>
        </div>

        {/* Custom Date Form (visible when preset === 'custom') */}
        {datePreset === 'custom' && (
          <form onSubmit={handleApplyCustomDates} className="mt-3 pt-3 border-t border-slate-800 flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <span>From:</span>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <span>To:</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs"
              />
            </div>
            <Button type="submit" size="sm" variant="primary" className="text-xs py-1 h-7">
              Apply Range
            </Button>
          </form>
        )}
      </Card>

      {/* Data Quality & Integrity Notice */}
      {overview && overview.data_quality && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <ShieldCheck size={16} className="text-indigo-400 shrink-0" />
            <span>
              Authoritative period dataset: <strong className="text-white">{overview.transaction_count}</strong> posted transactions.
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {overview.data_quality.uncategorized_count > 0 && (
              <Badge variant="warning" size="sm">
                <HelpCircle size={12} /> {overview.data_quality.uncategorized_count} Uncategorized ({formatINR(overview.data_quality.uncategorized_amount)})
              </Badge>
            )}
            {overview.data_quality.excluded_transfers_count > 0 && (
              <Badge variant="neutral" size="sm">
                {overview.data_quality.excluded_transfers_count} Transfers Excluded (Non-revenue)
              </Badge>
            )}
            {overview.data_quality.excluded_pending_count > 0 && (
              <Badge variant="info" size="sm">
                {overview.data_quality.excluded_pending_count} Pending Excluded ({formatINR(overview.data_quality.excluded_pending_amount)})
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* 1. Net Worth */}
          <Card className="p-5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
              <span>Current Net Worth</span>
              <Wallet size={14} className="text-indigo-400" />
            </p>
            <h3 className="text-2xl font-mono font-bold text-white tracking-tight">
              {netWorth ? formatINR(netWorth.net_worth) : formatINR(0)}
            </h3>
            {netWorth && (
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800">
                <span className="text-emerald-400 font-medium">Assets: {formatINR(netWorth.total_assets)}</span>
                <span className="text-rose-400 font-medium">Liab: {formatINR(netWorth.total_liabilities)}</span>
              </div>
            )}
          </Card>

          {/* 2. Total Income */}
          <Card className="p-5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
              <span>Operating Inflow</span>
              <ArrowDownRight size={14} className="text-emerald-400" />
            </p>
            <h3 className="text-2xl font-mono font-bold text-emerald-400 tracking-tight">
              {formatINR(overview.total_income)}
            </h3>
            {comparison && comparison.deltas && (
              <div className="mt-3 flex items-center gap-1.5 text-[11px] pt-2 border-t border-slate-800">
                {typeof comparison.deltas.income_percentage_delta === 'number' && (
                  <span
                    className={`font-semibold flex items-center gap-0.5 ${
                      comparison.deltas.income_sentiment === 'favorable' ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {comparison.deltas.income_delta_paise >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    {comparison.deltas.income_percentage_delta > 0 ? '+' : ''}
                    {comparison.deltas.income_percentage_delta}%
                  </span>
                )}
                <span className="text-slate-500">vs prior period</span>
              </div>
            )}
          </Card>

          {/* 3. Operating Expenses */}
          <Card className="p-5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
              <span>Operating Outflow</span>
              <ArrowUpRight size={14} className="text-rose-400" />
            </p>
            <h3 className="text-2xl font-mono font-bold text-rose-400 tracking-tight">
              {formatINR(overview.total_expenses)}
            </h3>
            <div className="mt-3 flex items-center justify-between text-[11px] pt-2 border-t border-slate-800">
              {overview.refunds_paise > 0 ? (
                <span className="text-slate-400">
                  Gross: {formatINR(overview.gross_expenses_paise / 100)} (Refunds: {formatINR(overview.refunds_paise / 100)})
                </span>
              ) : (
                <span className="text-slate-400">Daily Burn: {formatINR(overview.average_daily_spend)}/day</span>
              )}
            </div>
          </Card>

          {/* 4. Net Cash Flow & Savings Rate */}
          <Card className={`p-5 ${overview.net_cash_flow_paise >= 0 ? 'bg-indigo-950/20 border-indigo-900/40' : 'bg-rose-950/20 border-rose-900/40'}`}>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
              <span>Net Cash Flow</span>
              <PiggyBank size={14} className="text-indigo-400" />
            </p>
            <h3 className={`text-2xl font-mono font-bold tracking-tight ${overview.net_cash_flow_paise >= 0 ? 'text-white' : 'text-rose-400'}`}>
              {formatINR(overview.net_cash_flow)}
            </h3>
            <div className="mt-3 flex items-center justify-between text-[11px] pt-2 border-t border-slate-800">
              <span className="text-indigo-300 font-semibold">
                Savings Rate: {overview.savings_rate_percentage}%
              </span>
              <span className="text-slate-400 font-mono text-[10px]">{overview.days_in_period} days</span>
            </div>
          </Card>
        </div>
      )}

      {/* Main Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cash Flow Trends Chart (Span 2) */}
        <Card className="lg:col-span-2 p-5">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <TrendingUp size={16} className="text-indigo-400" /> Cash Flow Trajectory
              </span>
              <span className="text-xs font-normal text-slate-400">
                Inflow vs Outflow ({grouping.toUpperCase()})
              </span>
            </CardTitle>
          </CardHeader>

          <div className="h-[300px] w-full">
            {cashFlow && cashFlow.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cashFlow.trends}>
                  <defs>
                    <linearGradient id="colorInflow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="colorOutflow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="period_label"
                    stroke="#64748b"
                    fontSize={11}
                    tickMargin={8}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={11}
                    tickMargin={8}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                    formatter={(val: unknown) => [formatINR(val as number), '']}
                  />
                  <Area
                    type="monotone"
                    name="Income"
                    dataKey="income"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorInflow)"
                  />
                  <Area
                    type="monotone"
                    name="Expenses"
                    dataKey="expenses"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorOutflow)"
                  />
                  <Line
                    type="monotone"
                    name="Net Cash Flow"
                    dataKey="net_cash_flow"
                    stroke="#6366f1"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: '#6366f1' }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                No posted transactions found in this date window.
              </div>
            )}
          </div>
        </Card>

        {/* Category Breakdown (Donut) */}
        <Card className="p-5">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <PieIcon size={16} className="text-indigo-400" /> Category Outflow
              </span>
              <span className="text-xs font-normal text-slate-400">
                {categorySpending?.categories.length || 0} Categories
              </span>
            </CardTitle>
          </CardHeader>

          <div className="h-[300px] w-full">
            {categorySpending && categorySpending.categories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categorySpending.categories}
                    dataKey="total_amount"
                    nameKey="category_name"
                    innerRadius={60}
                    outerRadius={88}
                    paddingAngle={4}
                    stroke="none"
                  >
                    {categorySpending.categories.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color || CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                    formatter={(val: unknown) => [formatINR(val as number), 'Spend']}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={40}
                    iconType="circle"
                    formatter={(val) => <span className="text-[11px] text-slate-300">{val}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                No categorized expenses for this window.
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Secondary Intelligence: Top Merchants & Balance Sheet Structure */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Merchant Intelligence Ranking */}
        <Card className="p-5">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Tag size={16} className="text-indigo-400" /> Merchant Expenditure Ranking
              </span>
              <span className="text-xs font-normal text-slate-400">Top Outflows</span>
            </CardTitle>
          </CardHeader>

          <div className="divide-y divide-slate-800">
            {merchantSpending && merchantSpending.merchants.length > 0 ? (
              merchantSpending.merchants.slice(0, 6).map((m, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5">
                    <span className="text-[10px] font-mono font-bold text-slate-500 w-4">{idx + 1}.</span>
                    <div>
                      <div className="font-semibold text-white truncate max-w-[180px]">{m.merchant_name}</div>
                      <div className="text-[10px] text-slate-400">
                        {m.transaction_count} txn{m.transaction_count > 1 ? 's' : ''} • Avg {formatINR(m.average_ticket)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-bold text-slate-200">{formatINR(m.total_amount)}</div>
                    <div className="text-[10px] text-indigo-400 font-semibold">{m.percentage_of_total}%</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                No merchant spending recorded in this period.
              </div>
            )}
          </div>
        </Card>

        {/* Balance Sheet: Account Asset vs Liability Composition */}
        <Card className="p-5">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <CreditCard size={16} className="text-indigo-400" /> Account Liquidity & Liabilities
              </span>
              <span className="text-xs font-normal text-slate-400">Active Balances</span>
            </CardTitle>
          </CardHeader>

          <div className="space-y-4">
            {netWorth ? (
              <>
                {/* Assets Section */}
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 mb-2 flex items-center justify-between">
                    <span>Liquid & Investment Assets</span>
                    <span>{formatINR(netWorth.total_assets)}</span>
                  </div>
                  <div className="space-y-1.5">
                    {netWorth.asset_accounts.map((acc) => (
                      <div key={acc.id} className="flex items-center justify-between text-xs bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
                        <span className="font-medium text-slate-300 truncate max-w-[200px]">
                          {acc.name} <span className="text-[10px] text-slate-500">({acc.account_type})</span>
                        </span>
                        <span className="font-mono font-bold text-slate-100">{formatINR(acc.current_book_balance)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Liabilities Section */}
                {netWorth.liability_accounts.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-rose-400 mb-2 flex items-center justify-between">
                      <span>Liabilities & Credit Lines</span>
                      <span>{formatINR(netWorth.total_liabilities)}</span>
                    </div>
                    <div className="space-y-1.5">
                      {netWorth.liability_accounts.map((acc) => (
                        <div key={acc.id} className="flex items-center justify-between text-xs bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
                          <span className="font-medium text-slate-300 truncate max-w-[200px]">
                            {acc.name} <span className="text-[10px] text-slate-500">({acc.account_type})</span>
                          </span>
                          <span className="font-mono font-bold text-rose-400">{formatINR(acc.outstanding_liability)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="py-8 text-center text-xs text-slate-500">
                No active financial accounts found.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
