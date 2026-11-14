import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Flame,
  History,
  Layers,
  MoreVertical,
  Plus,
  RefreshCw,
  Sliders,
  Target,
  Trash2,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useBudgetStore } from '@/store/useBudgetStore';
import { useCategoryStore } from '@/store/useCategoryStore';
import type {
  BudgetAllocationProgressResponse,
  BudgetCreateRequest,
  BudgetRolloverRequest,
} from '@arthsavora/contracts';

export default function Budgets() {
  const {
    budgets,
    selectedBudget,
    budgetProgress,
    revisions,
    alerts,
    loading,
    progressLoading,
    fetchBudgets,
    selectBudget,
    createBudget,
    updateBudget,
    deleteBudget,
    rolloverBudget,
    addAllocation,
    updateAllocation,
    removeAllocation,
  } = useBudgetStore();

  const { categories, fetchCategories } = useCategoryStore();

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isAddAllocOpen, setIsAddAllocOpen] = useState(false);
  const [isEditAllocOpen, setIsEditAllocOpen] = useState<BudgetAllocationProgressResponse | null>(null);
  const [isRolloverOpen, setIsRolloverOpen] = useState(false);
  const [isRevisionsOpen, setIsRevisionsOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);

  // Form states
  const [newBudgetName, setNewBudgetName] = useState('');
  const [newBudgetType, setNewBudgetType] = useState('monthly');
  const [newStartDate, setNewStartDate] = useState('');
  const [newEndDate, setNewEndDate] = useState('');
  const [newTotalLimitINR, setNewTotalLimitINR] = useState('');
  const [newRecurrence, setNewRecurrence] = useState('monthly');

  // Allocation form states
  const [allocCategory, setAllocCategory] = useState('');
  const [allocAmountINR, setAllocAmountINR] = useState('');
  const [allocThreshold, setAllocThreshold] = useState('80');
  const [allocNotes, setAllocNotes] = useState('');
  const [editAllocAmountINR, setEditAllocAmountINR] = useState('');
  const [editAllocThreshold, setEditAllocThreshold] = useState('80');
  const [editRevisionReason, setEditRevisionReason] = useState('');

  // Rollover form states
  const [rolloverStartDate, setRolloverStartDate] = useState('');
  const [rolloverEndDate, setRolloverEndDate] = useState('');
  const [rolloverAdjustINR, setRolloverAdjustINR] = useState('');

  useEffect(() => {
    fetchBudgets();
    fetchCategories();
  }, [fetchBudgets, fetchCategories]);

  // Handle Create Budget
  const handleCreateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBudgetName || !newStartDate || !newEndDate || !newTotalLimitINR) {
      toast.error('Please fill in all required budget parameters.');
      return;
    }

    const totalPaise = Math.round(parseFloat(newTotalLimitINR) * 100);
    if (isNaN(totalPaise) || totalPaise < 0) {
      toast.error('Invalid budget limit amount.');
      return;
    }

    const payload: BudgetCreateRequest = {
      name: newBudgetName.trim(),
      budget_type: newBudgetType,
      start_date: newStartDate,
      end_date: newEndDate,
      total_allocated_paise: totalPaise,
      recurrence_interval: newRecurrence,
      currency: 'INR',
    };

    const created = await createBudget(payload);
    if (created) {
      toast.success(`Budget '${created.name}' established successfully.`);
      setIsCreateOpen(false);
      setNewBudgetName('');
      setNewTotalLimitINR('');
    } else {
      toast.error('Failed to create budget.');
    }
  };

  // Handle Add Allocation
  const handleAddAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBudget || !allocCategory || !allocAmountINR) {
      toast.error('Please select a category and specify allocation amount.');
      return;
    }

    const amountPaise = Math.round(parseFloat(allocAmountINR) * 100);
    const threshold = parseInt(allocThreshold, 10) || 80;

    const ok = await addAllocation(selectedBudget.id, {
      category_id: allocCategory,
      allocated_amount_paise: amountPaise,
      warning_threshold_percentage: threshold,
      notes: allocNotes.trim() || undefined,
    });

    if (ok) {
      toast.success('Category allocation added.');
      setIsAddAllocOpen(false);
      setAllocCategory('');
      setAllocAmountINR('');
      setAllocNotes('');
    } else {
      toast.error('Failed to add category allocation.');
    }
  };

  // Handle Edit Allocation
  const handleEditAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBudget || !isEditAllocOpen) return;

    const amountPaise = editAllocAmountINR ? Math.round(parseFloat(editAllocAmountINR) * 100) : undefined;
    const threshold = editAllocThreshold ? parseInt(editAllocThreshold, 10) : undefined;

    const ok = await updateAllocation(selectedBudget.id, isEditAllocOpen.allocation_id, {
      allocated_amount_paise: amountPaise,
      warning_threshold_percentage: threshold,
      revision_reason: editRevisionReason.trim() || 'Adjusted category allocation limit',
    });

    if (ok) {
      toast.success('Category allocation updated.');
      setIsEditAllocOpen(null);
      setEditRevisionReason('');
    } else {
      toast.error('Failed to update category allocation.');
    }
  };

  // Handle Rollover
  const handleRollover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBudget) return;

    const adjustPaise = rolloverAdjustINR ? Math.round(parseFloat(rolloverAdjustINR) * 100) : undefined;
    const payload: BudgetRolloverRequest = {
      new_start_date: rolloverStartDate || undefined,
      new_end_date: rolloverEndDate || undefined,
      adjust_allocation_paise: adjustPaise,
    };

    const rolled = await rolloverBudget(selectedBudget.id, payload);
    if (rolled) {
      toast.success(`Rolled over into new budget '${rolled.name}'.`);
      setIsRolloverOpen(false);
    } else {
      toast.error('Failed to roll over budget.');
    }
  };

  // Warning state badge helper
  const getWarningStateBadge = (state: string) => {
    switch (state) {
      case 'exceeded':
        return <Badge variant="expense">Exceeded</Badge>;
      case 'critical':
        return <Badge variant="expense">Critical (&gt;90%)</Badge>;
      case 'warning':
        return <Badge variant="warning">Warning (&gt;80%)</Badge>;
      case 'caution':
        return <Badge variant="warning">Caution (&gt;75%)</Badge>;
      default:
        return <Badge variant="income">Normal</Badge>;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Target className="text-indigo-500" size={32} />
            Personal Budgeting & Spending Controls
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic spending ceilings, linear run-rate projections, category limits, and threshold alert tracking.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {selectedBudget && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsRolloverOpen(true)}
                className="gap-1.5 text-xs text-slate-300"
              >
                <RefreshCw size={14} />
                Rollover Period
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsRevisionsOpen(true)}
                className="gap-1.5 text-xs text-slate-300"
              >
                <History size={14} />
                Revisions ({revisions.length})
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAlertsOpen(true)}
                className="gap-1.5 text-xs text-slate-300"
              >
                <Flame size={14} className={alerts.length > 0 ? 'text-amber-400' : ''} />
                Alerts ({alerts.length})
              </Button>
            </>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              const now = new Date();
              const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
              const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
              setNewStartDate(start);
              setNewEndDate(end);
              setNewBudgetName(`${now.toLocaleString('default', { month: 'long' })} ${now.getFullYear()} Budget`);
              setIsCreateOpen(true);
            }}
            className="gap-1.5 text-xs"
          >
            <Plus size={15} />
            Create Budget
          </Button>
        </div>
      </div>

      {/* Budget Selector Tabs */}
      {budgets.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Budgets:</span>
          {budgets.map((b) => (
            <button
              key={b.id}
              onClick={() => selectBudget(b.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 whitespace-nowrap border ${
                selectedBudget?.id === b.id
                  ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/50 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <span>{b.name}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {formatINR(Number(b.total_allocated))}
              </span>
              {b.status === 'active' && (
                <span className="h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20" />
              )}
            </button>
          ))}
        </div>
      )}

      {loading && !selectedBudget && (
        <div className="text-center py-16 text-slate-400 animate-pulse">
          Loading personal budgets and spending records...
        </div>
      )}

      {!loading && budgets.length === 0 && (
        <Card className="text-center py-16 border-dashed border-slate-800 bg-slate-900/20">
          <CardContent className="space-y-4">
            <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-full w-fit mx-auto">
              <Target size={36} />
            </div>
            <h3 className="text-lg font-bold text-white">No Budgets Configured</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              Create your first personal budget to set monthly spending ceilings, allocate limits to categories, and track progress against actual transactions.
            </p>
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                const now = new Date();
                const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
                const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
                setNewStartDate(start);
                setNewEndDate(end);
                setNewBudgetName(`${now.toLocaleString('default', { month: 'long' })} ${now.getFullYear()} Budget`);
                setIsCreateOpen(true);
              }}
              className="gap-2"
            >
              <Plus size={16} />
              Create First Budget
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Active Budget Content */}
      {selectedBudget && budgetProgress && (
        <div className="space-y-8">
          {/* Top 4 KPI Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Total Allocated */}
            <Card className="bg-slate-900/60 border-slate-800 p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Allocated</span>
                <Badge variant="brand" className="text-2xs uppercase">
                  {selectedBudget.recurrence_interval}
                </Badge>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold font-mono text-white">
                  {formatINR(Number(budgetProgress.total_allocated_amount))}
                </div>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                  <Calendar size={12} />
                  <span>{budgetProgress.start_date} to {budgetProgress.end_date}</span>
                </div>
              </div>
            </Card>

            {/* Card 2: Actual Spent */}
            <Card className="bg-slate-900/60 border-slate-800 p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Actual Spent</span>
                {getWarningStateBadge(budgetProgress.warning_state)}
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold font-mono text-white">
                  {formatINR(Number(budgetProgress.total_spent_amount))}
                </div>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                  <span className="font-mono font-semibold text-slate-300">
                    {budgetProgress.utilization_percentage.toFixed(1)}%
                  </span>
                  <span>of budget ceiling consumed</span>
                </div>
              </div>
            </Card>

            {/* Card 3: Remaining Capacity */}
            <Card className="bg-slate-900/60 border-slate-800 p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Remaining Capacity</span>
                {budgetProgress.overspent ? (
                  <Badge variant="expense" className="text-2xs">
                    OVERSPENT
                  </Badge>
                ) : (
                  <Badge variant="income" className="text-2xs">
                    AVAILABLE
                  </Badge>
                )}
              </div>
              <div className="mt-3">
                <div className={`text-2xl font-bold font-mono ${budgetProgress.overspent ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {formatINR(Number(budgetProgress.remaining_amount))}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {budgetProgress.overspent
                    ? 'Ceiling exceeded by eligible spend'
                    : 'Remaining spending headroom'}
                </div>
              </div>
            </Card>

            {/* Card 4: Run-Rate Projection */}
            <Card className="bg-slate-900/60 border-slate-800 p-5">
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Projected Period-End</span>
                {budgetProgress.linear_projection.projected_overspent ? (
                  <TrendingUp size={16} className="text-rose-400" />
                ) : (
                  <TrendingDown size={16} className="text-emerald-400" />
                )}
              </div>
              <div className="mt-3">
                <div className={`text-2xl font-bold font-mono ${budgetProgress.linear_projection.projected_overspent ? 'text-rose-400' : 'text-slate-100'}`}>
                  {formatINR(Number(budgetProgress.linear_projection.projected_period_end_spend))}
                </div>
                <div className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                  <span>Burn: {formatINR(Number(budgetProgress.linear_projection.daily_run_rate))}/day</span>
                  <span className={budgetProgress.linear_projection.projected_overspent ? 'text-rose-400' : 'text-emerald-400'}>
                    {budgetProgress.linear_projection.projected_overspent ? '+' : ''}
                    {formatINR(Number(budgetProgress.linear_projection.projected_variance))}
                  </span>
                </div>
              </div>
            </Card>
          </div>

          {/* Period Progress Timeline & Burn Rate Bar */}
          <Card className="bg-slate-900/50 border-slate-800 p-6 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Clock size={16} className="text-indigo-400" />
                  Period Progression vs Spending Burn Rate
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Day {budgetProgress.elapsed_days} of {budgetProgress.period_days} ({budgetProgress.period_elapsed_percentage.toFixed(0)}% elapsed) • {budgetProgress.remaining_days} days remaining
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs font-mono font-medium text-slate-300">
                  {formatINR(Number(budgetProgress.total_spent_amount))} / {formatINR(Number(budgetProgress.total_allocated_amount))}
                </span>
                <span className="text-xs text-slate-500 ml-1.5">
                  ({budgetProgress.utilization_percentage.toFixed(1)}%)
                </span>
              </div>
            </div>

            {/* Stacked Visual Bar */}
            <div className="space-y-1.5">
              <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden relative">
                {/* Time elapsed marker line */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-white/70 z-10"
                  style={{ left: `${Math.min(100, budgetProgress.period_elapsed_percentage)}%` }}
                  title={`Period Elapsed: ${budgetProgress.period_elapsed_percentage.toFixed(0)}%`}
                />
                {/* Spending progress bar */}
                <div
                  className={`h-full rounded-full transition-all ${
                    budgetProgress.utilization_percentage >= 100
                      ? 'bg-rose-500'
                      : budgetProgress.utilization_percentage >= 80
                      ? 'bg-amber-500'
                      : 'bg-indigo-500'
                  }`}
                  style={{ width: `${Math.min(100, budgetProgress.utilization_percentage)}%` }}
                />
              </div>
              <div className="flex justify-between text-2xs text-slate-500 font-mono">
                <span>Start ({budgetProgress.start_date})</span>
                <span className="text-slate-400">Time: {budgetProgress.period_elapsed_percentage.toFixed(0)}% | Spend: {budgetProgress.utilization_percentage.toFixed(0)}%</span>
                <span>End ({budgetProgress.end_date})</span>
              </div>
            </div>
          </Card>

          {/* Category Allocations Section */}
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers size={18} className="text-indigo-400" />
                  Category Spending Allocations ({budgetProgress.allocations.length})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Category ceilings enforce dedicated discipline across discretionary and fixed expenses.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddAllocOpen(true)}
                className="gap-1.5 text-xs text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/10"
              >
                <Plus size={14} />
                Add Category Limit
              </Button>
            </div>

            {/* Unallocated capacity banner */}
            {Number(budgetProgress.unallocated_capacity_amount) > 0 && (
              <div className="p-3.5 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-center justify-between text-xs">
                <span className="text-indigo-300 flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-indigo-400" />
                  Unallocated Buffer: <strong>{formatINR(Number(budgetProgress.unallocated_capacity_amount))}</strong> available for general living expenses or unexpected outflows.
                </span>
              </div>
            )}

            {/* Category Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {budgetProgress.allocations.map((alloc) => (
                <Card key={alloc.allocation_id} className="bg-slate-900/60 border-slate-800 p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2.5">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: alloc.category_color || '#6366f1' }}
                      />
                      <span className="font-semibold text-sm text-slate-100">{alloc.category_name}</span>
                    </div>
                    {getWarningStateBadge(alloc.warning_state)}
                  </div>

                  {/* Amounts */}
                  <div className="flex justify-between items-baseline pt-1">
                    <div>
                      <span className="text-xs text-slate-400">Spent: </span>
                      <span className="font-mono font-bold text-sm text-white">
                        {formatINR(Number(alloc.spent_amount))}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-slate-400">Ceiling: </span>
                      <span className="font-mono text-sm text-slate-300">
                        {formatINR(Number(alloc.allocated_amount))}
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar with warning threshold */}
                  <div className="space-y-1">
                    <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full ${
                          alloc.utilization_percentage >= 100
                            ? 'bg-rose-500'
                            : alloc.utilization_percentage >= alloc.warning_threshold_percentage
                            ? 'bg-amber-500'
                            : 'bg-indigo-500'
                        }`}
                        style={{ width: `${Math.min(100, alloc.utilization_percentage)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-2xs text-slate-500">
                      <span>{alloc.utilization_percentage.toFixed(0)}% used</span>
                      <span className={alloc.overspent ? 'text-rose-400 font-semibold' : 'text-slate-400'}>
                        {alloc.overspent ? 'Over by ' : 'Remaining: '}
                        {formatINR(Math.abs(Number(alloc.remaining_amount)))}
                      </span>
                    </div>
                  </div>

                  {/* Allocation Actions */}
                  <div className="flex justify-end gap-1.5 pt-2 border-t border-slate-800/80">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setIsEditAllocOpen(alloc);
                        setEditAllocAmountINR(alloc.allocated_amount.toString());
                        setEditAllocThreshold(alloc.warning_threshold_percentage.toString());
                      }}
                      className="h-7 px-2.5 text-2xs text-slate-400 hover:text-white"
                    >
                      <Sliders size={12} className="mr-1" />
                      Adjust
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={async () => {
                        if (confirm(`Remove category allocation '${alloc.category_name}' from budget?`)) {
                          await removeAllocation(selectedBudget.id, alloc.allocation_id, 'User removed category limit');
                          toast.success('Category allocation removed.');
                        }
                      }}
                      className="h-7 px-2 text-2xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                    >
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </Card>
              ))}

              {budgetProgress.allocations.length === 0 && (
                <div className="col-span-full text-center py-10 border border-dashed border-slate-800 rounded-xl bg-slate-900/20 text-slate-400 text-sm">
                  No category allocations defined yet. Click &quot;Add Category Limit&quot; to specify category ceilings.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Create Budget */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Establish New Personal Budget"
        description="Configure spending boundaries, period interval, and total allocation ceiling."
        size="md"
      >
        <form onSubmit={handleCreateBudget} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">Budget Name *</label>
            <Input
              value={newBudgetName}
              onChange={(e) => setNewBudgetName(e.target.value)}
              placeholder="e.g. November 2026 Household Budget"
              required
              className="mt-1"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Period Type</label>
              <select
                value={newBudgetType}
                onChange={(e) => setNewBudgetType(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="monthly">Monthly</option>
                <option value="custom_period">Custom Period</option>
                <option value="annual">Annual</option>
                <option value="flexible">Flexible</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Recurrence</label>
              <select
                value={newRecurrence}
                onChange={(e) => setNewRecurrence(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
                <option value="none">None (One-time)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Start Date *</label>
              <Input
                type="date"
                value={newStartDate}
                onChange={(e) => setNewStartDate(e.target.value)}
                required
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">End Date *</label>
              <Input
                type="date"
                value={newEndDate}
                onChange={(e) => setNewEndDate(e.target.value)}
                required
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Total Budget Limit (₹ INR) *</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={newTotalLimitINR}
              onChange={(e) => setNewTotalLimitINR(e.target.value)}
              placeholder="e.g. 50000"
              required
              className="mt-1 font-mono"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Budget
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Add Category Allocation */}
      <Modal
        isOpen={isAddAllocOpen}
        onClose={() => setIsAddAllocOpen(false)}
        title="Add Category Allocation Limit"
        description="Allocate a portion of your total budget ceiling to a specific expense category."
        size="md"
      >
        <form onSubmit={handleAddAllocation} className="space-y-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-300">Expense Category *</label>
            <select
              value={allocCategory}
              onChange={(e) => setAllocCategory(e.target.value)}
              className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              required
            >
              <option value="">Select category...</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.category_type})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Ceiling Amount (₹ INR) *</label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={allocAmountINR}
                onChange={(e) => setAllocAmountINR(e.target.value)}
                placeholder="e.g. 15000"
                required
                className="mt-1 font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Warning Threshold (%)</label>
              <select
                value={allocThreshold}
                onChange={(e) => setAllocThreshold(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="50">50%</option>
                <option value="75">75%</option>
                <option value="80">80% (Default)</option>
                <option value="90">90%</option>
                <option value="100">100%</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Notes / Discipline Strategy</label>
            <Input
              value={allocNotes}
              onChange={(e) => setAllocNotes(e.target.value)}
              placeholder="e.g. Strictly groceries, avoid high-ticket dining"
              className="mt-1"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsAddAllocOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Add Category Limit
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Edit Allocation */}
      <Modal
        isOpen={!!isEditAllocOpen}
        onClose={() => setIsEditAllocOpen(null)}
        title={`Adjust Limit: ${isEditAllocOpen?.category_name}`}
        description="Modify category allocation ceiling and record mandatory audit reason."
        size="md"
      >
        <form onSubmit={handleEditAllocation} className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Revised Amount (₹ INR) *</label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={editAllocAmountINR}
                onChange={(e) => setEditAllocAmountINR(e.target.value)}
                required
                className="mt-1 font-mono"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Warning Threshold (%)</label>
              <select
                value={editAllocThreshold}
                onChange={(e) => setEditAllocThreshold(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white"
              >
                <option value="50">50%</option>
                <option value="75">75%</option>
                <option value="80">80%</option>
                <option value="90">90%</option>
                <option value="100">100%</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Audit Revision Reason *</label>
            <Input
              value={editRevisionReason}
              onChange={(e) => setEditRevisionReason(e.target.value)}
              placeholder="e.g. Higher fuel price this month / family event"
              required
              className="mt-1"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsEditAllocOpen(null)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Apply Revision
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Rollover Budget */}
      <Modal
        isOpen={isRolloverOpen}
        onClose={() => setIsRolloverOpen(false)}
        title="Rollover Budget into Next Period"
        description="Clone budget parameters and category limits to subsequent period seamlessly."
        size="md"
      >
        <form onSubmit={handleRollover} className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Next Period Start (Optional)</label>
              <Input
                type="date"
                value={rolloverStartDate}
                onChange={(e) => setRolloverStartDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300">Next Period End (Optional)</label>
              <Input
                type="date"
                value={rolloverEndDate}
                onChange={(e) => setRolloverEndDate(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300">Adjusted Total Ceiling (₹ INR - Optional)</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={rolloverAdjustINR}
              onChange={(e) => setRolloverAdjustINR(e.target.value)}
              placeholder="Leave blank to maintain current ceiling"
              className="mt-1 font-mono"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="ghost" size="sm" onClick={() => setIsRolloverOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Execute Rollover
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Revision History */}
      <Modal
        isOpen={isRevisionsOpen}
        onClose={() => setIsRevisionsOpen(false)}
        title="Budget Audit Revision Ledger"
        description="Immutable record of every parameter and category allocation change."
        size="lg"
      >
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {revisions.map((rev) => (
            <div key={rev.id} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-1.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <Badge variant="brand">
                    Rev #{rev.revision_number}
                  </Badge>
                  <span className="uppercase text-slate-300">{rev.change_type.replace('_', ' ')}</span>
                </span>
                <span className="text-slate-500 font-mono text-2xs">
                  {new Date(rev.created_at).toLocaleString()}
                </span>
              </div>
              {rev.reason && (
                <p className="text-slate-300 italic">
                  &quot;{rev.reason}&quot;
                </p>
              )}
            </div>
          ))}
          {revisions.length === 0 && (
            <p className="text-center py-6 text-slate-500 text-xs">No audit revisions recorded yet.</p>
          )}
        </div>
      </Modal>

      {/* MODAL: Triggered Alerts */}
      <Modal
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        title="Threshold Crossing Alerts"
        description="Idempotent threshold alerts triggered when actual expenses crossed warning levels."
        size="lg"
      >
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {alerts.map((al) => (
            <div key={al.id} className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-1 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-amber-300 flex items-center gap-1.5">
                  <AlertTriangle size={14} />
                  {al.category_name ? `${al.category_name}: ` : 'Overall Budget: '}
                  {al.threshold_percentage}% Threshold Crossed
                </span>
                <span className="text-slate-400 font-mono text-2xs">
                  {new Date(al.created_at).toLocaleString()}
                </span>
              </div>
              <p className="text-slate-300">{al.message}</p>
              <div className="text-2xs text-slate-500 font-mono">
                Spend at trigger: {formatINR(Number(al.triggered_at_amount))} ({al.utilization_percentage.toFixed(1)}%)
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <p className="text-center py-6 text-slate-500 text-xs">No threshold alerts triggered for this budget period.</p>
          )}
        </div>
      </Modal>
    </div>
  );
}
