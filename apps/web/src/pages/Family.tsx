import React, { useEffect, useState } from 'react';
import {
  Users,
  Shield,
  Wallet,
  PieChart,
  ArrowRightLeft,
  Calendar,
  CheckCircle,
  AlertTriangle,
  Plus,
  Clock,
  Share2,
  Trash2,
  TrendingUp,
  CreditCard,
  UserCheck,
  ChevronRight,
  Info,
} from 'lucide-react';
import { useFamilyStore } from '../store/useFamilyStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';

export const Family: React.FC = () => {
  const {
    overview,
    profile,
    members,
    allocations,
    contributions,
    settlement,
    sharedAccounts,
    activities,
    isLoading,
    error,
    fetchOverview,
    fetchMembers,
    inviteMember,
    updateMemberRole,
    removeMember,
    fetchAllocations,
    createAllocation,
    fetchContributions,
    recordContribution,
    fetchSettlements,
    fetchSharedAccounts,
    shareAccount,
    revokeSharedAccount,
    fetchActivities,
  } = useFamilyStore();

  const [activeTab, setActiveTab] = useState<
    'overview' | 'members' | 'allocations' | 'settlements' | 'contributions' | 'activity'
  >('overview');

  // Modals state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');

  const [showAllocationModal, setShowAllocationModal] = useState(false);
  const [allocTxId, setAllocTxId] = useState('');
  const [allocMethod, setAllocMethod] = useState<'equal' | 'percentage' | 'fixed'>('equal');
  const [allocNotes, setAllocNotes] = useState('');

  const [showContributionModal, setShowContributionModal] = useState(false);
  const [contribMemberId, setContribMemberId] = useState('');
  const [contribPeriod, setContribPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [contribExpected, setContribExpected] = useState('');
  const [contribPaid, setContribPaid] = useState('');
  const [contribType, setContribType] = useState('monthly');

  const [showShareModal, setShowShareModal] = useState(false);
  const [shareAccountId, setShareAccountId] = useState('');
  const [shareScope, setShareScope] = useState('balance_only');

  useEffect(() => {
    fetchOverview();
    fetchMembers();
    fetchAllocations();
    fetchContributions();
    fetchSettlements();
    fetchSharedAccounts();
    fetchActivities();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;
    try {
      await inviteMember(inviteEmail, inviteRole);
      setInviteEmail('');
      setShowInviteModal(false);
    } catch {
      // Handled by store
    }
  };

  const handleCreateAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!allocTxId) return;
    try {
      await createAllocation({
        transaction_id: allocTxId,
        allocation_method: allocMethod,
        notes: allocNotes || undefined,
      });
      setAllocTxId('');
      setAllocNotes('');
      setShowAllocationModal(false);
    } catch {
      // Handled by store
    }
  };

  const handleRecordContribution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contribMemberId || !contribPeriod) return;
    try {
      const expPaise = Math.round(parseFloat(contribExpected || '0') * 100);
      const paidPaise = Math.round(parseFloat(contribPaid || '0') * 100);
      await recordContribution({
        member_user_id: contribMemberId,
        period: contribPeriod,
        expected_amount_paise: expPaise,
        paid_amount_paise: paidPaise,
        contribution_type: contribType,
      });
      setShowContributionModal(false);
      setContribExpected('');
      setContribPaid('');
    } catch {
      // Handled by store
    }
  };

  const handleShareAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shareAccountId) return;
    try {
      await shareAccount(shareAccountId, shareScope);
      setShareAccountId('');
      setShowShareModal(false);
    } catch {
      // Handled by store
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {profile?.household_name || 'Family Finance & Shared Household'}
            </h1>
            <Badge variant="brand" className="bg-primary/10 text-primary border-primary/20">
              Household Workspace
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Collaborative household budgeting, expense allocations, and settlements with zero-trust personal privacy.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => setShowInviteModal(true)}>
            <Users className="w-4 h-4 mr-2" />
            Invite Member
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowAllocationModal(true)}>
            <ArrowRightLeft className="w-4 h-4 mr-2" />
            New Allocation
          </Button>
          <Button size="sm" onClick={() => setShowContributionModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Record Contribution
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Household Income</span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            ₹{overview?.total_household_income_decimal?.toLocaleString('en-IN') ?? '0.00'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">This month inflows</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Household Expenses</span>
            <ArrowRightLeft className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            ₹{overview?.total_household_expense_decimal?.toLocaleString('en-IN') ?? '0.00'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">Shared outflows</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Net Savings</span>
            <Wallet className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            ₹{overview?.net_household_savings_decimal?.toLocaleString('en-IN') ?? '0.00'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">Pool surplus</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Shared Balances</span>
            <CreditCard className="w-4 h-4 text-primary" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            ₹{overview?.shared_account_balances_decimal?.toLocaleString('en-IN') ?? '0.00'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">Joint & shared accounts</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Budget Spent</span>
            <PieChart className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {overview?.budget_utilization_pct ?? '0.00'}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">{overview?.active_budgets_count ?? 0} active budgets</p>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('members')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'members'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Members & Privacy ({members.length})
        </button>
        <button
          onClick={() => setActiveTab('allocations')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'allocations'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Expense Allocations ({allocations.length})
        </button>
        <button
          onClick={() => setActiveTab('settlements')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'settlements'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Settlements & Net Standing
        </button>
        <button
          onClick={() => setActiveTab('contributions')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'contributions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Contributions Pool ({contributions.length})
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'activity'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Activity Timeline
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Spending Categories */}
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <PieChart className="w-4 h-4 text-primary" />
              Top Household Expense Categories
            </h3>
            {overview?.top_expense_categories && overview.top_expense_categories.length > 0 ? (
              <div className="space-y-3">
                {overview.top_expense_categories.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">{c.category}</span>
                    <span className="font-semibold text-foreground">
                      ₹{c.amount_decimal?.toLocaleString('en-IN') ?? '0.00'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No household expenses recorded this month yet.
              </p>
            )}
          </Card>

          {/* Recent Shared Transactions */}
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-primary" />
              Recent Shared Expenses
            </h3>
            {overview?.recent_shared_transactions && overview.recent_shared_transactions.length > 0 ? (
              <div className="space-y-3">
                {overview.recent_shared_transactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between border-b border-border/50 pb-2 text-sm">
                    <div>
                      <p className="font-medium text-foreground">{tx.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {tx.transaction_date} • Paid by {tx.paid_by}
                      </p>
                    </div>
                    <span className={`font-semibold ${tx.direction === 'inflow' ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {tx.direction === 'inflow' ? '+' : '-'}₹{tx.amount_decimal?.toLocaleString('en-IN')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No transactions recorded in this family workspace.
              </p>
            )}
          </Card>

          {/* Privacy Invariant Banner */}
          <Card className="p-5 lg:col-span-2 bg-muted/40 border-primary/20 space-y-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <Shield className="w-4 h-4" />
              Family Financial Boundary & Privacy Guarantee
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Family membership grants visibility only to accounts and transactions created directly inside this family
              workspace or explicitly shared. Personal workspace transactions, personal bank accounts, salaries, and
              investments remain completely invisible to all family members and administrators.
            </p>
          </Card>
        </div>
      )}

      {/* Tab 2: Members & Privacy */}
      {activeTab === 'members' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <Users className="w-4 h-4 text-primary" />
                Household Members
              </h3>
              <Button size="sm" onClick={() => setShowInviteModal(true)}>
                <UserCheck className="w-4 h-4 mr-2" />
                Invite Member
              </Button>
            </div>

            <div className="divide-y divide-border/60">
              {members.map((m) => (
                <div key={m.id} className="py-3 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                      {m.full_name?.charAt(0) || 'U'}
                    </div>
                    <div>
                      <p className="font-medium text-sm text-foreground">{m.full_name}</p>
                      <p className="text-xs text-muted-foreground">{m.email}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge variant="neutral" className="capitalize">
                      {m.role}
                    </Badge>
                    {m.role !== 'owner' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() => removeMember(m.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Shared Personal Accounts */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-primary" />
                  Selectively Shared Personal Accounts
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Personal accounts shared by members to display balances without exposing individual transaction details.
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setShowShareModal(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Share Account
              </Button>
            </div>

            {sharedAccounts.length > 0 ? (
              <div className="divide-y divide-border/60">
                {sharedAccounts.map((sa) => (
                  <div key={sa.id} className="py-3 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm text-foreground">{sa.account_name}</p>
                      <p className="text-xs text-muted-foreground">
                        Shared by {sa.shared_by_name} • Scope: <span className="font-medium">{sa.share_scope}</span>
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-sm text-foreground">
                        ₹{sa.current_balance_decimal?.toLocaleString('en-IN')}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => revokeSharedAccount(sa.account_id)}
                      >
                        Revoke
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No personal accounts shared into this workspace yet.
              </p>
            )}
          </Card>
        </div>
      )}

      {/* Tab 3: Allocations */}
      {activeTab === 'allocations' && (
        <Card className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-primary" />
                Expense Allocations
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Exact paise-level accounting distributions of shared expenses.
              </p>
            </div>
            <Button size="sm" onClick={() => setShowAllocationModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              New Allocation
            </Button>
          </div>

          {allocations.length > 0 ? (
            <div className="space-y-4">
              {allocations.map((a) => (
                <div key={a.id} className="p-4 rounded-lg border border-border bg-card/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm text-foreground">{a.transaction_description || 'Expense'}</p>
                      <p className="text-xs text-muted-foreground">
                        Method: <span className="font-semibold uppercase">{a.allocation_method}</span> • Version {a.version}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-sm text-foreground">₹{a.total_amount_decimal?.toLocaleString('en-IN')}</p>
                      <Badge variant="neutral" className="text-xs">
                        {a.status}
                      </Badge>
                    </div>
                  </div>

                  {/* Items Chips */}
                  <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
                    {a.items.map((it) => (
                      <div
                        key={it.id}
                        className="px-2.5 py-1 rounded bg-muted/60 text-xs flex items-center gap-1.5 border border-border/60"
                      >
                        <span className="text-muted-foreground">{it.member_name || 'Member'}:</span>
                        <span className="font-bold text-foreground">₹{it.assigned_share_decimal?.toLocaleString('en-IN')}</span>
                        {it.percentage && <span className="text-primary font-medium">({it.percentage}%)</span>}
                        {it.is_paid_by && <Badge className="text-[10px] py-0 px-1 ml-1">Payer</Badge>}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No expense allocations created yet. Click "New Allocation" to split a household expense.
            </p>
          )}
        </Card>
      )}

      {/* Tab 4: Settlements */}
      {activeTab === 'settlements' && (
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <div>
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                Member Net Standing
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Net Position = (Expenses Paid + Contributions Paid) - Allocated Share.
              </p>
            </div>

            {settlement?.member_settlements && settlement.member_settlements.length > 0 ? (
              <div className="divide-y divide-border/60">
                {settlement.member_settlements.map((ms) => (
                  <div key={ms.member_user_id} className="py-3 flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <p className="font-medium text-sm text-foreground">{ms.full_name}</p>
                      <p className="text-xs text-muted-foreground">
                        Paid: ₹{ms.total_expenses_paid_decimal?.toLocaleString('en-IN')} • Contributed: ₹
                        {ms.total_contributions_paid_decimal?.toLocaleString('en-IN')} • Share: ₹
                        {ms.total_allocated_share_decimal?.toLocaleString('en-IN')}
                      </p>
                    </div>

                    <div className="text-right">
                      <div
                        className={`font-bold text-sm ${
                          ms.net_position_paise > 0
                            ? 'text-emerald-500'
                            : ms.net_position_paise < 0
                            ? 'text-rose-500'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {ms.net_position_paise > 0 ? '+' : ''}₹{ms.net_position_decimal?.toLocaleString('en-IN')}
                      </div>
                      <Badge
                        variant={ms.status === 'surplus' ? 'income' : ms.status === 'deficit' ? 'expense' : 'neutral'}
                        className="text-xs capitalize"
                      >
                        {ms.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No settlement figures recorded for this period.
              </p>
            )}
          </Card>

          {/* Recommendations Card */}
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <Info className="w-4 h-4 text-primary" />
              Suggested Informational Settlements
            </h3>
            {settlement?.recommendations && settlement.recommendations.length > 0 ? (
              <div className="space-y-3">
                {settlement.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-primary/5 border border-primary/20 flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground">{rec.from_member_name}</span>
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      <span className="font-semibold text-foreground">{rec.to_member_name}</span>
                    </div>
                    <span className="font-bold text-primary">₹{rec.amount_decimal?.toLocaleString('en-IN')}</span>
                  </div>
                ))}
                <p className="text-[11px] text-muted-foreground italic">
                  Note: These are informational calculation netting suggestions. They do not execute bank transfers. Settle
                  externally or record transfers directly.
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                All household members are currently settled and balanced!
              </p>
            )}
          </Card>
        </div>
      )}

      {/* Tab 5: Contributions */}
      {activeTab === 'contributions' && (
        <Card className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                <Wallet className="w-4 h-4 text-primary" />
                Household Contributions Pool
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Monthly pool deposits and expected contributions from household members.
              </p>
            </div>
            <Button size="sm" onClick={() => setShowContributionModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Record Contribution
            </Button>
          </div>

          {contributions.length > 0 ? (
            <div className="divide-y divide-border/60">
              {contributions.map((c) => (
                <div key={c.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-foreground">{c.member_name || 'Member'}</p>
                    <p className="text-xs text-muted-foreground">
                      Period: <span className="font-medium">{c.period}</span> • Type: {c.contribution_type}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-sm text-foreground">
                      ₹{c.paid_amount_decimal?.toLocaleString('en-IN')}{' '}
                      <span className="text-xs text-muted-foreground font-normal">
                        / ₹{c.expected_amount_decimal?.toLocaleString('en-IN')}
                      </span>
                    </p>
                    <Badge variant="neutral" className="text-xs capitalize">
                      {c.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No contributions recorded yet. Click "Record Contribution" to add one.
            </p>
          )}
        </Card>
      )}

      {/* Tab 6: Activity */}
      {activeTab === 'activity' && (
        <Card className="p-5 space-y-4">
          <h3 className="font-semibold text-foreground flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            Family Activity Timeline
          </h3>
          {activities.length > 0 ? (
            <div className="space-y-4">
              {activities.map((a) => (
                <div key={a.id} className="flex items-start gap-3 text-sm border-l-2 border-primary/40 pl-3">
                  <div>
                    <p className="font-medium text-foreground">{a.title}</p>
                    <p className="text-xs text-muted-foreground">{a.description}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {new Date(a.created_at).toLocaleString('en-IN')} • By {a.actor_name || 'System'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No activity recorded in this family workspace yet.
            </p>
          )}
        </Card>
      )}

      {/* Invite Member Modal */}
      <Modal isOpen={showInviteModal} onClose={() => setShowInviteModal(false)} title="Invite Family Member">
        <form onSubmit={handleInvite} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Email Address</label>
            <Input
              type="email"
              placeholder="family.member@example.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Household Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background text-foreground"
            >
              <option value="member">Adult Member (Can view & allocate expenses)</option>
              <option value="admin">Administrator (Full household management)</option>
              <option value="restricted">Restricted Member (Dependent / Teen)</option>
              <option value="viewer">Viewer (Read-only observer)</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setShowInviteModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Send Invitation</Button>
          </div>
        </form>
      </Modal>

      {/* Create Allocation Modal */}
      <Modal isOpen={showAllocationModal} onClose={() => setShowAllocationModal(false)} title="Allocate Shared Expense">
        <form onSubmit={handleCreateAllocation} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Transaction ID (UUID)</label>
            <Input
              placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              value={allocTxId}
              onChange={(e) => setAllocTxId(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Allocation Method</label>
            <select
              value={allocMethod}
              onChange={(e: any) => setAllocMethod(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background text-foreground"
            >
              <option value="equal">Equal Split (All active members)</option>
              <option value="percentage">Percentage Allocation</option>
              <option value="fixed">Fixed Paise Allocation</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Notes / Purpose (Optional)</label>
            <Input
              placeholder="e.g. Monthly grocery split"
              value={allocNotes}
              onChange={(e) => setAllocNotes(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setShowAllocationModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Allocation</Button>
          </div>
        </form>
      </Modal>

      {/* Record Contribution Modal */}
      <Modal
        isOpen={showContributionModal}
        onClose={() => setShowContributionModal(false)}
        title="Record Household Pool Contribution"
      >
        <form onSubmit={handleRecordContribution} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Member</label>
            <select
              value={contribMemberId}
              onChange={(e) => setContribMemberId(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background text-foreground"
              required
            >
              <option value="">Select family member</option>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.full_name} ({m.role})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Period (YYYY-MM)</label>
              <Input
                type="text"
                placeholder="2026-11"
                value={contribPeriod}
                onChange={(e) => setContribPeriod(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Type</label>
              <select
                value={contribType}
                onChange={(e) => setContribType(e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background text-foreground"
              >
                <option value="monthly">Monthly</option>
                <option value="fixed">Fixed</option>
                <option value="one_time">One Time</option>
                <option value="voluntary">Voluntary</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Expected (₹)</label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={contribExpected}
                onChange={(e) => setContribExpected(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Paid (₹)</label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.00"
                value={contribPaid}
                onChange={(e) => setContribPaid(e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setShowContributionModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Save Contribution</Button>
          </div>
        </form>
      </Modal>

      {/* Share Account Modal */}
      <Modal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        title="Share Personal Account into Family"
      >
        <form onSubmit={handleShareAccount} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Account ID (UUID)</label>
            <Input
              placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
              value={shareAccountId}
              onChange={(e) => setShareAccountId(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Share Scope</label>
            <select
              value={shareScope}
              onChange={(e) => setShareScope(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background text-foreground"
            >
              <option value="balance_only">Balance Only (Shows total balance, hides transaction history)</option>
              <option value="summary_only">Summary Only (Shows balance & monthly inflow/outflow totals)</option>
              <option value="full_visibility">Full Visibility (Shows account & shared transaction items)</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setShowShareModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Confirm Sharing</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
export default Family;
