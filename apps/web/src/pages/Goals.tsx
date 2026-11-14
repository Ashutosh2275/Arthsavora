import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Archive,
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  Edit2,
  Flag,
  History,
  Layers,
  MinusCircle,
  Plus,
  PlusCircle,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useGoalStore } from '@/store/useGoalStore';
import type {
  GoalCreateRequest,
  GoalResponse,
  GoalUpdateRequest,
} from '@arthsavora/contracts';

export default function Goals() {
  const {
    goals,
    selectedGoal,
    selectedGoalProgress,
    activities,
    loading,
    activitiesLoading,
    fetchGoals,
    selectGoal,
    createGoal,
    updateGoal,
    deleteGoal,
    recordContribution,
    recordWithdrawal,
  } = useGoalStore();

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState<GoalResponse | null>(null);
  const [isContributeOpen, setIsContributeOpen] = useState<GoalResponse | null>(null);
  const [isWithdrawOpen, setIsWithdrawOpen] = useState<GoalResponse | null>(null);
  const [isActivityOpen, setIsActivityOpen] = useState<GoalResponse | null>(null);

  // Create form state
  const [name, setName] = useState('');
  const [targetAmountINR, setTargetAmountINR] = useState('');
  const [goalType, setGoalType] = useState('personal_savings');
  const [priority, setPriority] = useState('medium');
  const [targetDate, setTargetDate] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('#6366f1');

  // Activity form state
  const [activityAmountINR, setActivityAmountINR] = useState('');
  const [activityNotes, setActivityNotes] = useState('');

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editTargetINR, setEditTargetINR] = useState('');
  const [editTargetDate, setEditTargetDate] = useState('');
  const [editPriority, setEditPriority] = useState('medium');
  const [editStatus, setEditStatus] = useState('active');

  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);

  // Handle Create Goal
  const handleCreateGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !targetAmountINR) {
      toast.error('Please specify goal name and target amount.');
      return;
    }

    const targetPaise = Math.round(parseFloat(targetAmountINR) * 100);
    if (isNaN(targetPaise) || targetPaise <= 0) {
      toast.error('Target amount must be strictly greater than zero.');
      return;
    }

    const payload: GoalCreateRequest = {
      name: name.trim(),
      target_amount_paise: targetPaise,
      goal_type: goalType,
      priority,
      target_date: targetDate || null,
      description: description.trim() || undefined,
      color,
      currency: 'INR',
    };

    const created = await createGoal(payload);
    if (created) {
      toast.success(`Savings goal '${created.name}' established.`);
      setIsCreateOpen(false);
      setName('');
      setTargetAmountINR('');
      setDescription('');
    } else {
      toast.error('Failed to create savings goal.');
    }
  };

  // Handle Edit Goal
  const handleEditGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEditOpen) return;

    const targetPaise = editTargetINR ? Math.round(parseFloat(editTargetINR) * 100) : undefined;
    const ok = await updateGoal(isEditOpen.id, {
      name: editName.trim() || undefined,
      target_amount_paise: targetPaise,
      target_date: editTargetDate || null,
      priority: editPriority,
      status: editStatus,
    });

    if (ok) {
      toast.success('Financial goal updated.');
      setIsEditOpen(null);
    } else {
      toast.error('Failed to update goal.');
    }
  };

  // Handle Contribution
  const handleContribution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isContributeOpen || !activityAmountINR) return;

    const amountPaise = Math.round(parseFloat(activityAmountINR) * 100);
    if (isNaN(amountPaise) || amountPaise <= 0) {
      toast.error('Contribution amount must be greater than zero.');
      return;
    }

    const ok = await recordContribution(isContributeOpen.id, {
      amount_paise: amountPaise,
      notes: activityNotes.trim() || undefined,
    });

    if (ok) {
      toast.success(`Contributed ${formatINR(parseFloat(activityAmountINR))} to ${isContributeOpen.name}!`);
      setIsContributeOpen(null);
      setActivityAmountINR('');
      setActivityNotes('');
    } else {
      toast.error('Failed to record contribution.');
    }
  };

  // Handle Withdrawal
  const handleWithdrawal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isWithdrawOpen || !activityAmountINR) return;

    const amountPaise = Math.round(parseFloat(activityAmountINR) * 100);
    if (isNaN(amountPaise) || amountPaise <= 0) {
      toast.error('Withdrawal amount must be greater than zero.');
      return;
    }

    if (amountPaise > isWithdrawOpen.current_amount_paise) {
      toast.error(`Cannot withdraw more than current balance (${formatINR(Number(isWithdrawOpen.current_amount))}).`);
      return;
    }

    const ok = await recordWithdrawal(isWithdrawOpen.id, {
      amount_paise: amountPaise,
      notes: activityNotes.trim() || undefined,
    });

    if (ok) {
      toast.success(`Withdrew ${formatINR(parseFloat(activityAmountINR))} from ${isWithdrawOpen.name}.`);
      setIsWithdrawOpen(null);
      setActivityAmountINR('');
      setActivityNotes('');
    } else {
      toast.error('Failed to record withdrawal.');
    }
  };

  // Totals calculations
  const totalTargetPaise = goals.reduce((acc, g) => acc + g.target_amount_paise, 0);
  const totalSavedPaise = goals.reduce((acc, g) => acc + g.current_amount_paise, 0);
  const overallCompletionRate = totalTargetPaise > 0 ? (totalSavedPaise / totalTargetPaise) * 100 : 0;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Trophy className="text-indigo-500" size={32} />
            Financial Goals & Milestone Tracking
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Track emergency funds, large asset savings, vacation reserves, and debt retirement with auditable activity ledgers.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setIsCreateOpen(true)}
          className="gap-1.5 text-xs"
        >
          <Plus size={15} />
          Establish New Goal
        </Button>
      </div>

      {/* Top 4 Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-900/60 border-slate-800 p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Target Capital</span>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white">
              {formatINR(totalTargetPaise / 100)}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Across {goals.length} target milestone{goals.length !== 1 ? 's' : ''}
            </div>
          </div>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800 p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Accumulated</span>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-emerald-400">
              {formatINR(totalSavedPaise / 100)}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {overallCompletionRate.toFixed(1)}% of aggregate targets achieved
            </div>
          </div>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800 p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Remaining to Fund</span>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-slate-200">
              {formatINR(Math.max(0, totalTargetPaise - totalSavedPaise) / 100)}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Capital required to complete all milestones
            </div>
          </div>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800 p-5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Goals</span>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-indigo-400">
              {goals.filter((g) => g.status === 'active').length}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {goals.filter((g) => g.status === 'completed').length} completed milestone{goals.filter((g) => g.status === 'completed').length !== 1 ? 's' : ''}
            </div>
          </div>
        </Card>
      </div>

      {loading && goals.length === 0 && (
        <div className="text-center py-16 text-slate-400 animate-pulse">
          Loading financial goals and contribution ledgers...
        </div>
      )}

      {!loading && goals.length === 0 && (
        <Card className="text-center py-16 border-dashed border-slate-800 bg-slate-900/20">
          <CardContent className="space-y-4">
            <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-full w-fit mx-auto">
              <Trophy size={36} />
            </div>
            <h3 className="text-lg font-bold text-white">No Financial Goals Defined</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              Start building your financial freedom by defining milestones: emergency funds, travel reserves, vehicle purchases, or debt repayments.
            </p>
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsCreateOpen(true)}
              className="gap-2"
            >
              <Plus size={16} />
              Establish First Goal
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Goals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {goals.map((g) => {
          const compRate = g.target_amount_paise > 0 ? (g.current_amount_paise / g.target_amount_paise) * 100 : 0;
          const isDone = g.status === 'completed' || g.current_amount_paise >= g.target_amount_paise;

          return (
            <Card
              key={g.id}
              className={`bg-slate-900/60 border-slate-800 p-5 space-y-4 transition-all hover:border-slate-700 ${
                isDone ? 'ring-1 ring-emerald-500/30' : ''
              }`}
            >
              {/* Header */}
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: g.color || '#6366f1' }}
                    />
                    <h3 className="font-semibold text-base text-white">{g.name}</h3>
                  </div>
                  <div className="flex items-center gap-2 text-2xs text-slate-400 uppercase">
                    <span>{g.goal_type.replace('_', ' ')}</span>
                    <span>•</span>
                    <span className={g.priority === 'high' ? 'text-amber-400 font-semibold' : ''}>
                      {g.priority} priority
                    </span>
                  </div>
                </div>

                <Badge
                  variant={isDone ? 'income' : g.status === 'paused' ? 'neutral' : 'brand'}
                >
                  {isDone ? 'Completed' : g.status}
                </Badge>
              </div>

              {/* Balances */}
              <div className="space-y-1">
                <div className="flex justify-between items-baseline">
                  <span className="text-2xl font-bold font-mono text-white">
                    {formatINR(Number(g.current_amount))}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Target: {formatINR(Number(g.target_amount))}
                  </span>
                </div>
                <div className="text-2xs text-slate-400 flex justify-between">
                  <span>
                    {compRate.toFixed(1)}% funded
                  </span>
                  <span>
                    {formatINR(Math.max(0, g.target_amount_paise - g.current_amount_paise) / 100)} remaining
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isDone ? 'bg-emerald-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${Math.min(100, compRate)}%` }}
                />
              </div>

              {/* Target Date / Pacing Indicator */}
              <div className="flex justify-between items-center text-xs text-slate-400 pt-1">
                <span className="flex items-center gap-1.5">
                  <Calendar size={13} />
                  {g.target_date ? `Target: ${g.target_date}` : 'Open-ended'}
                </span>
                <button
                  onClick={async () => {
                    await selectGoal(g.id);
                    setIsActivityOpen(g);
                  }}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <History size={12} />
                  Ledger
                </button>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsContributeOpen(g);
                      setActivityAmountINR('');
                      setActivityNotes('');
                    }}
                    className="h-8 px-2.5 text-xs text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                  >
                    <PlusCircle size={13} className="mr-1" />
                    Contribute
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={g.current_amount_paise <= 0}
                    onClick={() => {
                      setIsWithdrawOpen(g);
                      setActivityAmountINR('');
                      setActivityNotes('');
                    }}
                    className="h-8 px-2.5 text-xs text-amber-400 border-amber-500/30 hover:bg-amber-500/10"
                  >
                    <MinusCircle size={13} className="mr-1" />
                    Withdraw
                  </Button>
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setIsEditOpen(g);
                      setEditName(g.name);
                      setEditTargetINR(g.target_amount.toString());
                      setEditTargetDate(g.target_date || '');
                      setEditPriority(g.priority);
                      setEditStatus(g.status);
                    }}
                    className="h-8 w-8 p-0 text-slate-400 hover:text-white"
                  >
                    <Edit2 size={13} />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      if (confirm(`Archive financial goal '${g.name}'?`)) {
                        await deleteGoal(g.id);
                        toast.success('Goal archived.');
                      }
                    }}
                    className="h-8 w-8 p-0 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* MODAL: Establish Goal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Establish Financial Savings Goal"
        description="Define a target amount, milestone date, and allocation priority."
        size="md"
      >
        <form onSubmit={handleCreateGoal} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">Goal Name *</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. 6-Month Emergency Fund"
              required
              className="mt-1"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Target Amount (₹ INR) *</label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={targetAmountINR}
                onChange={(e) => setTargetAmountINR(e.target.value)}
                placeholder="e.g. 250000"
                required
                className="mt-1 font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Goal Type</label>
              <select
                value={goalType}
                onChange={(e) => setGoalType(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="emergency_fund">Emergency Fund</option>
                <option value="personal_savings">Personal Savings</option>
                <option value="travel">Travel & Vacation</option>
                <option value="vehicle">Vehicle Purchase</option>
                <option value="home">Home / Real Estate</option>
                <option value="education">Education</option>
                <option value="debt_repayment">Debt Repayment</option>
                <option value="custom">Custom Milestone</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Target Completion Date</label>
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="high">High Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="low">Low Priority</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Description / Memo</label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Safe deposit liquid reserve for contingencies"
              className="mt-1"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Establish Goal
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Contribute */}
      <Modal
        isOpen={!!isContributeOpen}
        onClose={() => setIsContributeOpen(null)}
        title={`Contribute to ${isContributeOpen?.name}`}
        description="Allocate funds into this goal's accumulated balance."
        size="md"
      >
        <form onSubmit={handleContribution} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">Contribution Amount (₹ INR) *</label>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              value={activityAmountINR}
              onChange={(e) => setActivityAmountINR(e.target.value)}
              placeholder="e.g. 5000"
              required
              className="mt-1 font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Audit Notes / Transaction Ref</label>
            <Input
              value={activityNotes}
              onChange={(e) => setActivityNotes(e.target.value)}
              placeholder="e.g. Monthly salary savings deposit"
              className="mt-1"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsContributeOpen(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Confirm Contribution
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Withdraw */}
      <Modal
        isOpen={!!isWithdrawOpen}
        onClose={() => setIsWithdrawOpen(null)}
        title={`Withdraw from ${isWithdrawOpen?.name}`}
        description="Return allocated savings to unallocated workspace liquidity."
        size="md"
      >
        <form onSubmit={handleWithdrawal} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">
              Withdrawal Amount (₹ INR) * (Max: {formatINR(Number(isWithdrawOpen?.current_amount || 0))})
            </label>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              max={Number(isWithdrawOpen?.current_amount || 0)}
              value={activityAmountINR}
              onChange={(e) => setActivityAmountINR(e.target.value)}
              placeholder="e.g. 2000"
              required
              className="mt-1 font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Audit Reason / Purpose</label>
            <Input
              value={activityNotes}
              onChange={(e) => setActivityNotes(e.target.value)}
              placeholder="e.g. Paid vehicle deposit downpayment"
              className="mt-1"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsWithdrawOpen(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Confirm Withdrawal
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Edit Goal */}
      <Modal
        isOpen={!!isEditOpen}
        onClose={() => setIsEditOpen(null)}
        title={`Edit Goal: ${isEditOpen?.name}`}
        description="Update milestone targets, target date, or priority."
        size="md"
      >
        <form onSubmit={handleEditGoal} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">Goal Name</label>
            <Input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Target Amount (₹ INR)</label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={editTargetINR}
                onChange={(e) => setEditTargetINR(e.target.value)}
                className="mt-1 font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Status</label>
              <select
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Target Date</label>
              <Input
                type="date"
                value={editTargetDate}
                onChange={(e) => setEditTargetDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Priority</label>
              <select
                value={editPriority}
                onChange={(e) => setEditPriority(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="high">High Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="low">Low Priority</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsEditOpen(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Activity Ledger */}
      <Modal
        isOpen={!!isActivityOpen}
        onClose={() => setIsActivityOpen(null)}
        title={`Audit Activity Ledger: ${isActivityOpen?.name}`}
        description="Chronological ledger of all contributions and withdrawals."
        size="lg"
      >
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {activitiesLoading && (
            <div className="text-center py-6 text-slate-500 text-xs">Loading ledger entries...</div>
          )}

          {!activitiesLoading && activities.map((act) => (
            <div
              key={act.id}
              className={`p-3.5 rounded-xl border flex items-center justify-between text-xs ${
                act.activity_type === 'contribution'
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : 'border-amber-500/30 bg-amber-500/5'
              }`}
            >
              <div className="flex items-center gap-2.5">
                {act.activity_type === 'contribution' ? (
                  <ArrowDownLeft className="text-emerald-400" size={16} />
                ) : (
                  <ArrowUpRight className="text-amber-400" size={16} />
                )}
                <div>
                  <div className="font-semibold text-white capitalize">
                    {act.activity_type}
                  </div>
                  {act.notes && <div className="text-2xs text-slate-400">{act.notes}</div>}
                </div>
              </div>

              <div className="text-right">
                <div
                  className={`font-mono font-bold ${
                    act.activity_type === 'contribution' ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {act.activity_type === 'contribution' ? '+' : '-'}
                  {formatINR(Number(act.amount))}
                </div>
                <div className="text-2xs text-slate-500 font-mono">
                  Balance: {formatINR(act.resulting_balance_paise / 100)}
                </div>
              </div>
            </div>
          ))}

          {!activitiesLoading && activities.length === 0 && (
            <p className="text-center py-6 text-slate-500 text-xs">No activity entries recorded for this goal yet.</p>
          )}
        </div>
      </Modal>
    </div>
  );
}
