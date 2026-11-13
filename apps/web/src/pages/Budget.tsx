import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { Target, Sparkles } from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import type { BudgetStatusItem, BudgetForecastResponse, ExpenseCategory } from '@arthsavora/contracts';

export default function Budget() {
  const [budgets, setBudgets] = useState<BudgetStatusItem[]>([]);
  const [forecast, setForecast] = useState<BudgetForecastResponse | null>(null);
  const [newBudget, setNewBudget] = useState<{ category: ExpenseCategory; limit: string }>({
    category: 'Food',
    limit: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      const [bRes, fRes] = await Promise.all([
        api.get<BudgetStatusItem[]>('/budget/status'),
        api.get<BudgetForecastResponse>('/budget/forecast'),
      ]);
      setBudgets(bRes.data);
      setForecast(fRes.data);
    } catch (err) {
      console.error('Failed to load budget data:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSetBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBudget.limit) return;
    setIsSubmitting(true);

    try {
      await api.post('/budget/', {
        category: newBudget.category,
        limit: parseFloat(newBudget.limit),
      });
      toast.success(`Budget for ${newBudget.category} updated`);
      setNewBudget({ category: 'Food', limit: '' });
      fetchData();
    } catch {
      toast.error('Failed to update budget');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <header>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Target className="text-indigo-400" size={24} /> Budgeting & Forecasting
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Category limits, consumption velocity, and time-series spending projections.
        </p>
      </header>

      {/* AI Forecast Card */}
      <Card className="border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 p-6">
        <div className="flex items-center gap-2 text-indigo-300 text-xs font-bold uppercase tracking-wider mb-3">
          <Sparkles size={16} /> Projected Spending For Next Month
        </div>
        <div className="flex items-baseline gap-4">
          <h3 className="font-mono text-4xl font-bold text-white">
            {formatINR(forecast?.prediction || 0)}
          </h3>
          <span className="text-xs text-slate-400">
            Status: <span className="text-indigo-300 font-semibold">{forecast?.status || 'Active'}</span>
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-3 max-w-lg leading-relaxed">
          ARIMA time-series model projection computed from your historical transaction volume.
        </p>
      </Card>

      {/* Set Budget Form */}
      <Card>
        <form onSubmit={handleSetBudget} className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Category
            </label>
            <select
              value={newBudget.category}
              onChange={(e) =>
                setNewBudget({ ...newBudget, category: e.target.value as ExpenseCategory })
              }
              className="w-full rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
            >
              <option value="Food">Food</option>
              <option value="Travel">Travel</option>
              <option value="Shopping">Shopping</option>
              <option value="Bills">Bills</option>
              <option value="Entertainment">Entertainment</option>
              <option value="Health">Health</option>
              <option value="Housing">Housing</option>
            </select>
          </div>

          <div className="flex-1 w-full">
            <Input
              label="Monthly Limit (₹)"
              type="number"
              placeholder="10000"
              value={newBudget.limit}
              onChange={(e) => setNewBudget({ ...newBudget, limit: e.target.value })}
              required
            />
          </div>

          <Button type="submit" size="md" className="w-full sm:w-auto" isLoading={isSubmitting}>
            Set Limit
          </Button>
        </form>
      </Card>

      {/* Budget Progress Bars */}
      <div className="space-y-4">
        {budgets.map((b) => (
          <div key={b.category} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-bold text-sm text-white">{b.category}</h4>
              <span className="font-mono text-xs text-slate-400">
                {formatINR(b.spent)} / <span className="text-indigo-400 font-semibold">{formatINR(b.limit)}</span>
              </span>
            </div>

            <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-700 ${
                  b.percent > 90 ? 'bg-rose-500' : 'bg-indigo-500'
                }`}
                style={{ width: `${Math.min(100, b.percent)}%` }}
              />
            </div>

            <div className="flex justify-between mt-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              <span>{b.percent.toFixed(0)}% consumed</span>
              <span>{formatINR(b.remaining)} remaining</span>
            </div>
          </div>
        ))}

        {budgets.length === 0 && (
          <div className="py-12 text-center text-xs text-slate-500">
            No active budget limits configured. Define a category limit above.
          </div>
        )}
      </div>
    </div>
  );
}
