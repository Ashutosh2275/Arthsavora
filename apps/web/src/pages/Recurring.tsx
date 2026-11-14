import React, { useEffect, useState } from 'react';
import {
  Calendar,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  Repeat,
  CheckCircle2,
  XCircle,
  Sparkles,
  Plus,
  CreditCard,
  AlertTriangle,
  TrendingUp,
  Layers,
  Tv,
  Zap,
  Home,
  Shield,
  Search,
  Pause,
  Play,
  Trash2,
  Link2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { FinancialAmount } from '@/components/ui/financial-amount';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Alert } from '@/components/ui/alert';
import { useRecurringStore } from '@/store/useRecurringStore';
import { useSubscriptionStore } from '@/store/useSubscriptionStore';
import type {
  OccurrenceResponse,
  RecurringDefinitionCreateRequest,
  RecurringDirection,
  RecurringFrequency,
  SubscriptionCreateRequest,
} from '@arthsavora/contracts';

type ActiveTab = 'commitments' | 'schedules' | 'subscriptions' | 'suggestions';

export const Recurring: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('commitments');
  const [windowDays, setWindowDays] = useState<number>(30);

  // Modals
  const [showAddRecurringModal, setShowAddRecurringModal] = useState(false);
  const [showAddSubscriptionModal, setShowAddSubscriptionModal] = useState(false);
  const [matchingOccurrence, setMatchingOccurrence] = useState<OccurrenceResponse | null>(null);
  const [matchTransactionId, setMatchTransactionId] = useState('');

  // Stores
  const {
    definitions,
    commitments,
    suggestions,
    loading,
    commitmentsLoading,
    detecting,
    error,
    fetchDefinitions,
    fetchCommitments,
    fetchSuggestions,
    runDetection,
    createDefinition,
    pauseDefinition,
    resumeDefinition,
    cancelDefinition,
    skipOccurrence,
    confirmOccurrence,
    matchOccurrence,
    confirmSuggestion,
    dismissSuggestion,
  } = useRecurringStore();

  const {
    subscriptions,
    fetchSubscriptions,
    createSubscription,
    cancelSubscription,
  } = useSubscriptionStore();

  useEffect(() => {
    fetchDefinitions();
    fetchCommitments(windowDays);
    fetchSubscriptions();
    fetchSuggestions();
  }, [windowDays]);

  // Form State - Recurring Definition
  const [recName, setRecName] = useState('');
  const [recDirection, setRecDirection] = useState<RecurringDirection>('outflow');
  const [recAmount, setRecAmount] = useState('');
  const [recFrequency, setRecFrequency] = useState<RecurringFrequency>('monthly');
  const [recDayOfMonth, setRecDayOfMonth] = useState('1');
  const [recStartDate, setRecStartDate] = useState(new Date().toISOString().split('T')[0]);

  // Form State - Subscription
  const [subName, setSubName] = useState('');
  const [subProvider, setSubProvider] = useState('');
  const [subAmount, setSubAmount] = useState('');
  const [subFrequency, setSubFrequency] = useState<'weekly' | 'monthly' | 'quarterly' | 'annual'>('monthly');
  const [subStartDate, setSubStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [subNextBilling, setSubNextBilling] = useState(new Date().toISOString().split('T')[0]);
  const [subTrialEnd, setSubTrialEnd] = useState('');

  const handleCreateRecurring = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountPaise = Math.round(parseFloat(recAmount) * 100);
    if (isNaN(amountPaise) || amountPaise <= 0) return;

    const payload: RecurringDefinitionCreateRequest = {
      name: recName,
      direction: recDirection,
      expected_amount_paise: amountPaise,
      frequency: recFrequency,
      day_of_month: recFrequency === 'monthly' ? parseInt(recDayOfMonth, 10) : undefined,
      start_date: recStartDate,
    };

    const res = await createDefinition(payload);
    if (res) {
      setShowAddRecurringModal(false);
      setRecName('');
      setRecAmount('');
    }
  };

  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountPaise = Math.round(parseFloat(subAmount) * 100);
    if (isNaN(amountPaise) || amountPaise <= 0) return;

    const payload: SubscriptionCreateRequest = {
      name: subName,
      provider_name: subProvider || undefined,
      expected_amount_paise: amountPaise,
      billing_frequency: subFrequency,
      start_date: subStartDate,
      next_billing_date: subNextBilling,
      trial_end_date: subTrialEnd || undefined,
      create_recurring_definition: true,
    };

    const res = await createSubscription(payload);
    if (res) {
      setShowAddSubscriptionModal(false);
      setSubName('');
      setSubProvider('');
      setSubAmount('');
      setSubTrialEnd('');
      fetchCommitments(windowDays);
      fetchDefinitions();
    }
  };

  const handleMatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!matchingOccurrence || !matchTransactionId.trim()) return;

    const ok = await matchOccurrence(matchingOccurrence.id, matchTransactionId.trim());
    if (ok) {
      setMatchingOccurrence(null);
      setMatchTransactionId('');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Repeat className="w-6 h-6 text-primary" />
            Recurring & Commitments
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Anticipate forward-looking cash flow, manage subscriptions, and reconcile scheduled payments.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => runDetection(180)}
            disabled={detecting}
            className="flex items-center gap-1.5"
          >
            <Sparkles className="w-4 h-4 text-amber-500" />
            {detecting ? 'Scanning History...' : 'Detect Recurring'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAddSubscriptionModal(true)}
            className="flex items-center gap-1.5"
          >
            <Tv className="w-4 h-4 text-indigo-500" />
            + Subscription
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAddRecurringModal(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            + Recurring Activity
          </Button>
        </div>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {/* Tabs Navigation */}
      <div className="flex border-b border-border gap-2">
        <button
          onClick={() => setActiveTab('commitments')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'commitments'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Clock className="w-4 h-4" />
          Upcoming Commitments
        </button>
        <button
          onClick={() => setActiveTab('schedules')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'schedules'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Layers className="w-4 h-4" />
          Recurring Schedules ({definitions.length})
        </button>
        <button
          onClick={() => setActiveTab('subscriptions')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'subscriptions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Tv className="w-4 h-4" />
          Subscriptions ({subscriptions.length})
        </button>
        <button
          onClick={() => setActiveTab('suggestions')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'suggestions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Sparkles className="w-4 h-4 text-amber-500" />
          Pattern Suggestions ({suggestions.length})
        </button>
      </div>

      {/* Tab 1: Commitments View */}
      {activeTab === 'commitments' && (
        <div className="space-y-6">
          {/* Horizon Selector */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Horizon Window:</span>
            <div className="flex rounded-lg border border-border p-1 bg-muted/30">
              {[7, 30, 90].map((d) => (
                <button
                  key={d}
                  onClick={() => setWindowDays(d)}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                    windowDays === d
                      ? 'bg-background shadow text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Next {d} Days
                </button>
              ))}
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
                <span>Expected Outflow</span>
                <ArrowUpRight className="w-4 h-4 text-rose-500" />
              </div>
              <div className="text-2xl font-bold mt-2 text-rose-600 dark:text-rose-400">
                <FinancialAmount amount={Number(commitments?.total_expected_outflow ?? 0)} currency="INR" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">Due in next {windowDays} days</p>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
                <span>Expected Inflow</span>
                <ArrowDownLeft className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-2xl font-bold mt-2 text-emerald-600 dark:text-emerald-400">
                <FinancialAmount amount={Number(commitments?.total_expected_inflow ?? 0)} currency="INR" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">Scheduled receipts</p>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
                <span>Net Forward Commitment</span>
                <TrendingUp className="w-4 h-4 text-primary" />
              </div>
              <div className="text-2xl font-bold mt-2 text-foreground">
                <FinancialAmount amount={Number(commitments?.net_commitment ?? 0)} currency="INR" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">Inflow minus Outflow</p>
            </div>

            <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
                <span>Normalized Monthly Outflow</span>
                <Repeat className="w-4 h-4 text-indigo-500" />
              </div>
              <div className="text-2xl font-bold mt-2 text-indigo-600 dark:text-indigo-400">
                <FinancialAmount amount={Number(commitments?.normalized_monthly_expenses ?? 0)} currency="INR" />
              </div>
              <p className="text-xs text-muted-foreground mt-1">Annualized: ₹{(Number(commitments?.normalized_annual_expenses ?? 0)).toLocaleString()}</p>
            </div>
          </div>

          {/* Type Breakdown Cards */}
          {commitments?.commitments_by_type && commitments.commitments_by_type.length > 0 && (
            <div className="p-4 rounded-xl border border-border bg-card">
              <h3 className="text-sm font-semibold text-foreground mb-3">Commitment Breakdown by Category</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                {commitments.commitments_by_type.map((t) => (
                  <div key={t.type_name} className="p-2.5 rounded-lg border border-border/60 bg-muted/20">
                    <span className="text-xs text-muted-foreground block truncate">{t.type_name}</span>
                    <span className="text-sm font-bold text-foreground block mt-1">
                      <FinancialAmount amount={Number(t.total_amount)} currency="INR" />
                    </span>
                    <span className="text-[10px] text-muted-foreground">{t.count} occurrence(s)</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upcoming Occurrences Timeline */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Upcoming Occurrences</h3>
                <p className="text-xs text-muted-foreground">Expected financial events due in the active window.</p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-muted font-medium text-muted-foreground">
                {commitments?.upcoming_occurrences?.length || 0} scheduled
              </span>
            </div>

            {!commitments?.upcoming_occurrences || commitments.upcoming_occurrences.length === 0 ? (
              <EmptyState
                icon={<Calendar className="h-8 w-8" />}
                title="No upcoming commitments"
                description={`No scheduled occurrences due in the next ${windowDays} days.`}
              />
            ) : (
              <div className="divide-y divide-border">
                {commitments.upcoming_occurrences.map((occ) => (
                  <div key={occ.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-muted/10 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg mt-0.5 ${occ.direction === 'inflow' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600'}`}>
                        {occ.direction === 'inflow' ? <ArrowDownLeft className="w-5 h-5" /> : <ArrowUpRight className="w-5 h-5" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground text-sm">{occ.recurring_name || 'Scheduled Activity'}</span>
                          <Badge
                            variant={
                              occ.status === 'confirmed' || occ.status === 'matched'
                                ? 'income'
                                : occ.status === 'overdue'
                                ? 'expense'
                                : occ.status === 'due'
                                ? 'warning'
                                : 'neutral'
                            }
                          >
                            {occ.status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {new Date(occ.expected_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                          </span>
                          {occ.notes && <span>• {occ.notes}</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 self-end sm:self-center">
                      <div className="text-right">
                        <span className={`text-base font-bold block ${occ.direction === 'inflow' ? 'text-emerald-600' : 'text-foreground'}`}>
                          <FinancialAmount amount={Number(occ.expected_amount)} currency={occ.currency} />
                        </span>
                        {occ.amount_variance_paise !== null && occ.amount_variance_paise !== undefined && occ.amount_variance_paise !== 0 && (
                          <span className="text-[10px] text-muted-foreground">
                            Variance: {occ.amount_variance_paise > 0 ? '+' : ''}₹{(occ.amount_variance_paise / 100).toFixed(2)}
                          </span>
                        )}
                      </div>

                      {occ.status !== 'confirmed' && occ.status !== 'matched' && occ.status !== 'skipped' && (
                        <div className="flex items-center gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => confirmOccurrence(occ.id)}
                            title="Confirm occurrence without transaction"
                          >
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setMatchingOccurrence(occ)}
                            title="Reconcile with transaction"
                          >
                            <Link2 className="w-4 h-4 text-primary" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => skipOccurrence(occ.id, 'User skipped')}
                            title="Skip occurrence"
                          >
                            <XCircle className="w-4 h-4 text-muted-foreground hover:text-rose-500" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Recurring Schedules */}
      {activeTab === 'schedules' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Active Recurring Schedules</h3>
                <p className="text-xs text-muted-foreground">Governing rules generating expected future occurrences.</p>
              </div>
              <Button size="sm" onClick={() => setShowAddRecurringModal(true)}>
                + New Schedule
              </Button>
            </div>

            {definitions.length === 0 ? (
              <EmptyState
                icon={<Repeat className="h-8 w-8" />}
                title="No recurring schedules defined"
                description="Set up recurring salary, rent, utilities, or EMIs to automate forward-looking cash flow."
                action={
                  <Button size="sm" onClick={() => setShowAddRecurringModal(true)}>
                    + Add Recurring Schedule
                  </Button>
                }
              />
            ) : (
              <div className="divide-y divide-border">
                {definitions.map((defn) => (
                  <div key={defn.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-muted/10 transition-colors">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground text-base">{defn.name}</span>
                        <Badge
                          variant={defn.status === 'active' ? 'income' : defn.status === 'paused' ? 'warning' : 'neutral'}
                        >
                          {defn.status}
                        </Badge>
                        <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground capitalize font-medium">
                          {defn.frequency} {defn.interval > 1 ? `(every ${defn.interval})` : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                        {defn.category_name && <span>Category: {defn.category_name}</span>}
                        {defn.account_name && <span>• Account: {defn.account_name}</span>}
                        <span>• Next Due: {new Date(defn.next_expected_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className={`text-lg font-bold block ${defn.direction === 'inflow' ? 'text-emerald-600' : 'text-foreground'}`}>
                          <FinancialAmount amount={Number(defn.expected_amount)} currency={defn.currency} />
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          ₹{(defn.normalized_monthly_paise / 100).toLocaleString()}/mo
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {defn.status === 'active' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => pauseDefinition(defn.id)}
                            title="Pause schedule"
                          >
                            <Pause className="w-3.5 h-3.5" />
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => resumeDefinition(defn.id)}
                            title="Resume schedule"
                          >
                            <Play className="w-3.5 h-3.5 text-emerald-600" />
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => cancelDefinition(defn.id)}
                          title="Cancel schedule"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Subscriptions */}
      {activeTab === 'subscriptions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-foreground">Subscriptions & Memberships</h3>
              <p className="text-xs text-muted-foreground">Digital services, streaming, SaaS, and club renewals.</p>
            </div>
            <Button size="sm" onClick={() => setShowAddSubscriptionModal(true)}>
              + New Subscription
            </Button>
          </div>

          {subscriptions.length === 0 ? (
            <EmptyState
              icon={<Tv className="h-8 w-8" />}
              title="No subscriptions tracked"
              description="Track Netflix, Spotify, Prime, AWS, gym, and software memberships to monitor renewal deadlines and costs."
              action={
                <Button size="sm" onClick={() => setShowAddSubscriptionModal(true)}>
                  + Add Subscription
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {subscriptions.map((sub) => (
                <div key={sub.id} className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-foreground text-sm">{sub.name}</h4>
                      {sub.provider_name && <span className="text-xs text-muted-foreground">{sub.provider_name}</span>}
                    </div>
                    <Badge
                      variant={sub.status === 'active' ? 'income' : sub.status === 'trial' ? 'warning' : 'neutral'}
                    >
                      {sub.status}
                    </Badge>
                  </div>

                  <div className="flex items-baseline justify-between pt-1 border-t border-border/50">
                    <div>
                      <span className="text-xs text-muted-foreground block capitalize">{sub.billing_frequency}</span>
                      <span className="text-lg font-bold text-foreground">
                        <FinancialAmount amount={Number(sub.expected_amount)} currency={sub.currency} />
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-muted-foreground block">Monthly Cost</span>
                      <span className="text-sm font-semibold text-primary">
                        ₹{(sub.estimated_monthly_paise / 100).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground space-y-1 bg-muted/20 p-2 rounded-lg">
                    <div className="flex justify-between">
                      <span>Next Renewal:</span>
                      <span className="font-medium text-foreground">
                        {new Date(sub.next_billing_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </span>
                    </div>
                    {sub.trial_end_date && (
                      <div className="flex justify-between text-amber-600">
                        <span>Trial Ends:</span>
                        <span className="font-medium">{sub.trial_end_date}</span>
                      </div>
                    )}
                    {sub.payment_method_display && (
                      <div className="flex justify-between">
                        <span>Payment:</span>
                        <span className="font-medium text-foreground">{sub.payment_method_display}</span>
                      </div>
                    )}
                  </div>

                  {sub.status !== 'cancelled' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                      onClick={() => cancelSubscription(sub.id)}
                    >
                      Cancel Subscription
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Pattern Suggestions */}
      {activeTab === 'suggestions' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
            <div className="text-xs text-muted-foreground space-y-1">
              <span className="font-semibold text-foreground block text-sm">Explainable Pattern Intelligence</span>
              Patterns are inferred by analyzing recurring intervals, repeated amounts, and merchant similarities across verified transaction history. Confirming a suggestion creates an authoritative schedule. Dismissing prevents future prompts.
            </div>
          </div>

          {suggestions.length === 0 ? (
            <EmptyState
              icon={<Sparkles className="h-8 w-8 text-amber-500" />}
              title="No recurring patterns detected"
              description="Click 'Detect Recurring' to scan your transaction history for repeat payments, rent, salaries, or subscriptions."
              action={
                <Button size="sm" onClick={() => runDetection(180)}>
                  Scan Transaction History
                </Button>
              }
            />
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-card overflow-hidden">
              {suggestions.map((sugg) => (
                <div key={sugg.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-muted/10 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground text-sm">{sugg.merchant_name}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 font-semibold">
                        {(Number(sugg.confidence_score) * 100).toFixed(0)}% Confidence
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground capitalize font-medium">
                        {sugg.suggested_frequency}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-0.5">
                      <p>Description: {sugg.normalized_description}</p>
                      <p>
                        Based on {sugg.evidence_count} transactions between {sugg.first_seen_date} and {sugg.last_seen_date}.
                        Est. next occurrence: {sugg.estimated_next_date}.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end md:self-center">
                    <div className="text-right">
                      <span className="text-base font-bold text-foreground block">
                        <FinancialAmount amount={Number(sugg.suggested_amount)} currency={sugg.currency} />
                      </span>
                      {sugg.min_amount_paise !== sugg.max_amount_paise && (
                        <span className="text-[10px] text-muted-foreground">
                          Range: ₹{(sugg.min_amount_paise / 100).toFixed(0)} - ₹{(sugg.max_amount_paise / 100).toFixed(0)}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => confirmSuggestion(sugg.id, { is_subscription: false })}
                      >
                        Confirm Recurring
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => confirmSuggestion(sugg.id, { is_subscription: true })}
                      >
                        As Subscription
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => dismissSuggestion(sugg.id, 'User dismissed')}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Add Recurring Definition */}
      <Modal
        isOpen={showAddRecurringModal}
        onClose={() => setShowAddRecurringModal(false)}
        title="Create Recurring Financial Activity"
      >
        <form onSubmit={handleCreateRecurring} className="space-y-4">
          <Input
            label="Name / Title"
            placeholder="e.g. Monthly Apartment Rent, HDFC Home Loan, Gym"
            value={recName}
            onChange={(e) => setRecName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-foreground block mb-1">Direction</label>
              <select
                className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm"
                value={recDirection}
                onChange={(e) => setRecDirection(e.target.value as RecurringDirection)}
              >
                <option value="outflow">Outflow (Expense / Payment)</option>
                <option value="inflow">Inflow (Salary / Income)</option>
              </select>
            </div>

            <Input
              label="Expected Amount (₹)"
              type="number"
              step="0.01"
              placeholder="e.g. 25000.00"
              value={recAmount}
              onChange={(e) => setRecAmount(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-foreground block mb-1">Frequency</label>
              <select
                className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm"
                value={recFrequency}
                onChange={(e) => setRecFrequency(e.target.value as RecurringFrequency)}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Biweekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="semi_annual">Semi-Annual</option>
                <option value="annual">Annual</option>
              </select>
            </div>

            {recFrequency === 'monthly' && (
              <Input
                label="Day of Month"
                type="number"
                min="1"
                max="31"
                value={recDayOfMonth}
                onChange={(e) => setRecDayOfMonth(e.target.value)}
                required
              />
            )}
          </div>

          <Input
            label="Start Date"
            type="date"
            value={recStartDate}
            onChange={(e) => setRecStartDate(e.target.value)}
            required
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setShowAddRecurringModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Recurring Schedule'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Add Subscription */}
      <Modal
        isOpen={showAddSubscriptionModal}
        onClose={() => setShowAddSubscriptionModal(false)}
        title="Add Subscription or Membership"
      >
        <form onSubmit={handleCreateSubscription} className="space-y-4">
          <Input
            label="Subscription Name"
            placeholder="e.g. Netflix Premium 4K, Spotify Duo, AWS"
            value={subName}
            onChange={(e) => setSubName(e.target.value)}
            required
          />

          <Input
            label="Provider / Merchant"
            placeholder="e.g. Netflix India, Spotify AB, Amazon"
            value={subProvider}
            onChange={(e) => setSubProvider(e.target.value)}
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Expected Amount (₹)"
              type="number"
              step="0.01"
              placeholder="e.g. 649.00"
              value={subAmount}
              onChange={(e) => setSubAmount(e.target.value)}
              required
            />

            <div>
              <label className="text-xs font-medium text-foreground block mb-1">Billing Frequency</label>
              <select
                className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm"
                value={subFrequency}
                onChange={(e) => setSubFrequency(e.target.value as any)}
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Start Date"
              type="date"
              value={subStartDate}
              onChange={(e) => setSubStartDate(e.target.value)}
              required
            />

            <Input
              label="Next Billing Date"
              type="date"
              value={subNextBilling}
              onChange={(e) => setSubNextBilling(e.target.value)}
              required
            />
          </div>

          <Input
            label="Trial End Date (Optional)"
            type="date"
            value={subTrialEnd}
            onChange={(e) => setSubTrialEnd(e.target.value)}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setShowAddSubscriptionModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Save Subscription
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Match Occurrence */}
      <Modal
        isOpen={!!matchingOccurrence}
        onClose={() => setMatchingOccurrence(null)}
        title="Reconcile Occurrence with Transaction"
      >
        <form onSubmit={handleMatchSubmit} className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Associate this expected occurrence ({matchingOccurrence?.recurring_name} on {matchingOccurrence?.expected_date}) with an actual posted transaction ID.
          </p>

          <Input
            label="Transaction UUID"
            placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
            value={matchTransactionId}
            onChange={(e) => setMatchTransactionId(e.target.value)}
            required
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" type="button" onClick={() => setMatchingOccurrence(null)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Reconcile Match
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Recurring;
