import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { Target, ShieldCheck, Plus, Trash2, Lightbulb, Clock } from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import type { GoalResponse, GoalInsightResponse } from '@arthsavora/contracts';

export default function Goals() {
  const [goals, setGoals] = useState<GoalResponse[]>([]);
  const [insights, setInsights] = useState<GoalInsightResponse | null>(null);
  const [newGoal, setNewGoal] = useState({
    name: '',
    target_amount: '',
    current_amount: '',
    category: 'Savings',
  });
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAll = async () => {
    try {
      const [gRes, iRes] = await Promise.all([
        api.get<GoalResponse[]>('/goals/'),
        api.get<GoalInsightResponse>('/goals/insights'),
      ]);
      setGoals(gRes.data);
      setInsights(iRes.data);
    } catch (err) {
      console.error('Failed to fetch goals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleAddGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGoal.name || !newGoal.target_amount) return;
    setIsSubmitting(true);

    try {
      await api.post('/goals/', {
        name: newGoal.name,
        target_amount: parseFloat(newGoal.target_amount),
        current_amount: parseFloat(newGoal.current_amount) || 0,
        category: newGoal.category,
      });
      toast.success('Financial milestone established');
      setNewGoal({ name: '', target_amount: '', current_amount: '', category: 'Savings' });
      fetchAll();
    } catch {
      toast.error('Failed to create goal');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteGoal = async (id: string) => {
    try {
      await api.delete(`/goals/${id}`);
      toast.success('Goal removed');
      fetchAll();
    } catch {
      toast.error('Failed to delete goal');
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <header>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Target className="text-indigo-400" size={24} /> Financial Milestones
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Goal timelines, savings velocity, and asset allocation insights.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Create Form & Portfolio Insights */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
              <Plus size={14} /> Create Goal
            </h3>

            <form onSubmit={handleAddGoal} className="space-y-4">
              <Input
                label="Goal Name"
                placeholder="e.g. Emergency Fund"
                value={newGoal.name}
                onChange={(e) => setNewGoal({ ...newGoal, name: e.target.value })}
                required
              />

              <Input
                label="Target Amount (₹)"
                type="number"
                placeholder="500000"
                value={newGoal.target_amount}
                onChange={(e) => setNewGoal({ ...newGoal, target_amount: e.target.value })}
                required
              />

              <Input
                label="Current Savings (₹)"
                type="number"
                placeholder="0"
                value={newGoal.current_amount}
                onChange={(e) => setNewGoal({ ...newGoal, current_amount: e.target.value })}
              />

              <Button type="submit" size="md" className="w-full mt-2" isLoading={isSubmitting}>
                Establish Goal
              </Button>
            </form>
          </Card>

          {insights && (
            <Card className="border-indigo-500/20 bg-indigo-950/20 p-5">
              <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-3">
                <Lightbulb size={14} /> Strategy Recommendation
              </div>
              {insights.recommendations.map((rec, i) => (
                <div key={i} className="space-y-2 text-xs">
                  <div className="inline-block rounded-full bg-indigo-600/30 border border-indigo-500/30 px-2 py-0.5 text-[10px] font-bold text-indigo-300 uppercase">
                    {rec.type} Profile
                  </div>
                  <p className="text-slate-300 leading-relaxed italic">{rec.text}</p>
                  <div className="pt-3 border-t border-slate-800 text-slate-400">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Estimated Monthly Surplus</span>
                    <span className="font-mono text-base font-bold text-emerald-400">{formatINR(insights.surplus)}</span>
                  </div>
                </div>
              ))}
            </Card>
          )}
        </div>

        {/* Right Column: Active Goals */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 px-1">
            Active Milestones
          </h3>

          {goals.map((goal) => {
            const progress = goal.target_amount > 0
              ? Math.min(100, (goal.current_amount / goal.target_amount) * 100)
              : 0;

            return (
              <div
                key={goal.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 transition-all hover:border-slate-700"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400">
                      <ShieldCheck size={20} />
                    </div>
                    <div>
                      <h4 className="text-base font-bold text-white">{goal.name}</h4>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">
                        Target: {formatINR(goal.target_amount)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteGoal(goal.id)}
                    className="rounded-lg p-1.5 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-all"
                    aria-label="Delete milestone"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-400 font-mono">
                      {formatINR(goal.current_amount)} saved
                    </span>
                    <span className="font-mono font-bold text-indigo-400">
                      {progress.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-500 h-full transition-all duration-700"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-slate-800/60 pt-3 text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Clock size={14} className="text-indigo-400" />
                    <span>Est. Target: {goal.predicted_completion_date || 'Projecting...'}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">
                    Remaining: {formatINR(Math.max(0, goal.target_amount - goal.current_amount))}
                  </span>
                </div>
              </div>
            );
          })}

          {!loading && goals.length === 0 && (
            <div className="py-20 text-center text-xs text-slate-500 rounded-2xl border border-dashed border-slate-800">
              No milestones established. Define your first savings goal.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
