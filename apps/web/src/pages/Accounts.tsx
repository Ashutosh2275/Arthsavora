import React, { useEffect, useState } from 'react';
import useAccountStore from '@/store/useAccountStore';
import {
  Landmark,
  CreditCard,
  Wallet,
  PiggyBank,
  Plus,
  RefreshCw,
  Archive,
  RotateCcw,
  XCircle,
  ExternalLink,
  History,
  TrendingDown,
  TrendingUp,
  Shield,
  Clock,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { formatINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { toast } from 'sonner';
import type {
  AccountResponse,
  AccountCreateRequest,
  AccountType,
  AccountBalanceSnapshotCreateRequest,
} from '@arthsavora/contracts';

export default function Accounts() {
  const {
    accounts,
    selectedAccount,
    balanceHistory,
    loading,
    historyLoading,
    fetchAccounts,
    setSelectedAccount,
    createAccount,
    archiveAccount,
    restoreAccount,
    closeAccount,
    fetchBalanceHistory,
    recordSnapshot,
  } = useAccountStore();

  const [activeTab, setActiveTab] = useState<'all' | 'bank' | 'card' | 'wallet' | 'loan'>('all');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState(false);
  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false);
  const [closingDate, setClosingDate] = useState(new Date().toISOString().split('T')[0]);

  // Add Account Form State
  const [formData, setFormData] = useState<AccountCreateRequest>({
    name: '',
    account_type: 'savings',
    currency: 'INR',
    institution_name: '',
    masked_identifier: '',
    opening_balance: '0.00',
    opening_date: new Date().toISOString().split('T')[0],
    credit_limit: '',
    due_date: '',
    minimum_due: '',
    statement_balance: '',
    outstanding_liability: '',
    original_principal: '',
    outstanding_principal: '',
    interest_rate: undefined,
    repayment_amount: '',
    loan_due_date: '',
    provider_name: '',
    provider_account_id: '',
    description: '',
  });

  // Snapshot Form State
  const [snapshotData, setSnapshotData] = useState<AccountBalanceSnapshotCreateRequest>({
    balance_type: 'provider_reported',
    balance_amount: '',
    currency: 'INR',
    source: 'manual',
    source_reference: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Aggregate metrics
  const netLiquidAssetsPaise = accounts
    .filter((a) => a.status === 'active' && !['credit_card', 'loan', 'loan_account'].includes(a.account_type))
    .reduce((acc, a) => acc + (a.available_balance_paise ?? a.current_book_balance_paise), 0);

  const totalLiabilitiesPaise = accounts
    .filter((a) => a.status === 'active' && ['credit_card', 'loan', 'loan_account'].includes(a.account_type))
    .reduce((acc, a) => acc + (a.outstanding_liability_paise ?? 0), 0);

  const totalCreditLimitPaise = accounts
    .filter((a) => a.status === 'active' && a.account_type === 'credit_card' && a.balances?.credit_limit_paise)
    .reduce((acc, a) => acc + (a.balances.credit_limit_paise ?? 0), 0);

  const activeAccountsCount = accounts.filter((a) => a.status === 'active').length;

  // Filtering
  const filteredAccounts = accounts.filter((acc) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'bank') return ['savings', 'current', 'salary', 'bank', 'business_bank', 'business_current', 'fixed_deposit', 'recurring_deposit'].includes(acc.account_type);
    if (activeTab === 'card') return ['credit_card', 'business_credit_card'].includes(acc.account_type);
    if (activeTab === 'wallet') return ['wallet', 'digital_wallet', 'cash', 'petty_cash', 'business_cash'].includes(acc.account_type);
    if (activeTab === 'loan') return ['loan', 'loan_account'].includes(acc.account_type);
    return true;
  });

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Account name is required');
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await createAccount(formData);
      if (res.success) {
        toast.success(`Account '${formData.name}' created successfully`);
        setIsAddModalOpen(false);
        // Reset form
        setFormData({
          name: '',
          account_type: 'savings',
          currency: 'INR',
          institution_name: '',
          masked_identifier: '',
          opening_balance: '0.00',
          opening_date: new Date().toISOString().split('T')[0],
          description: '',
        });
      } else {
        toast.error(res.error || 'Failed to create account');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchive = async (id: string) => {
    const res = await archiveAccount(id);
    if (res.success) {
      toast.success('Account archived');
    } else {
      toast.error(res.error || 'Failed to archive account');
    }
  };

  const handleRestore = async (id: string) => {
    const res = await restoreAccount(id);
    if (res.success) {
      toast.success('Account restored to active');
    } else {
      toast.error(res.error || 'Failed to restore account');
    }
  };

  const handleClose = async () => {
    if (!selectedAccount) return;
    setIsSubmitting(true);
    try {
      const res = await closeAccount(selectedAccount.id, closingDate);
      if (res.success) {
        toast.success(`Account closed effective ${closingDate}`);
        setIsCloseModalOpen(false);
        setIsDetailModalOpen(false);
      } else {
        toast.error(res.error || 'Failed to close account');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRecordSnapshotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccount || !snapshotData.balance_amount) return;
    setIsSubmitting(true);
    try {
      const res = await recordSnapshot(selectedAccount.id, snapshotData);
      if (res.success) {
        toast.success('Balance snapshot recorded');
        setIsSnapshotModalOpen(false);
        setSnapshotData({
          balance_type: 'provider_reported',
          balance_amount: '',
          currency: selectedAccount.currency,
          source: 'manual',
          source_reference: '',
        });
      } else {
        toast.error(res.error || 'Failed to record snapshot');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const openAccountDetails = (acc: AccountResponse) => {
    setSelectedAccount(acc);
    fetchBalanceHistory(acc.id);
    setIsDetailModalOpen(true);
  };

  const getAccountIcon = (type: string) => {
    if (['credit_card', 'business_credit_card'].includes(type)) return <CreditCard className="text-amber-400" size={20} />;
    if (['wallet', 'digital_wallet', 'cash', 'petty_cash'].includes(type)) return <Wallet className="text-emerald-400" size={20} />;
    if (['loan', 'loan_account'].includes(type)) return <TrendingDown className="text-rose-400" size={20} />;
    if (['investment', 'fixed_deposit', 'recurring_deposit'].includes(type)) return <PiggyBank className="text-purple-400" size={20} />;
    return <Landmark className="text-indigo-400" size={20} />;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="income">Active</Badge>;
      case 'archived':
        return <Badge variant="warning">Archived</Badge>;
      case 'closed':
        return <Badge variant="neutral">Closed</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Landmark className="text-indigo-500" size={32} />
            Financial Accounts
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Unified balances, credit limits, loan tracking, and verified point-in-time snapshots.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAccounts()}
            disabled={loading}
            className="flex items-center gap-2 border-slate-700 text-slate-300 hover:text-white"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </Button>
          <Button
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
          >
            <Plus size={16} />
            <span>Add Account</span>
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Liquid Assets</span>
            <TrendingUp size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 tabular-nums">
            {formatINR(netLiquidAssetsPaise / 100)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Available across bank & cash accounts</p>
        </Card>

        <Card className="p-5 border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Liabilities</span>
            <TrendingDown size={16} className="text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 mt-2 tabular-nums">
            {formatINR(totalLiabilitiesPaise / 100)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Credit cards & loan obligations</p>
        </Card>

        <Card className="p-5 border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Credit Limit</span>
            <CreditCard size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-300 mt-2 tabular-nums">
            {formatINR(totalCreditLimitPaise / 100)}
          </div>
          <p className="text-xs text-slate-500 mt-1">Sanctioned revolving credit line</p>
        </Card>

        <Card className="p-5 border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Active Accounts</span>
            <Shield size={16} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 tabular-nums">
            {activeAccountsCount}
          </div>
          <p className="text-xs text-slate-500 mt-1">{accounts.length} total mapped entities</p>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {[
          { key: 'all', label: 'All Accounts' },
          { key: 'bank', label: 'Bank & Savings' },
          { key: 'card', label: 'Credit Cards' },
          { key: 'wallet', label: 'Cash & Wallets' },
          { key: 'loan', label: 'Loans & EMI' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === tab.key
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Accounts List / Cards */}
      {loading ? (
        <div className="py-16 text-center text-slate-500">
          <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
          Loading accounts...
        </div>
      ) : filteredAccounts.length === 0 ? (
        <Card className="p-12 text-center border-slate-800 bg-slate-900/40">
          <Landmark className="mx-auto text-slate-600 mb-3" size={40} />
          <h3 className="text-base font-semibold text-slate-300">No accounts found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {activeTab === 'all'
              ? 'Get started by adding your primary bank account, cash wallet, or credit card.'
              : `No accounts in the '${activeTab}' category. Click 'Add Account' to register one.`}
          </p>
          <Button
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="mt-4 bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            <Plus size={16} className="mr-1.5" />
            Add Account
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredAccounts.map((acc) => {
            const isCard = ['credit_card', 'business_credit_card'].includes(acc.account_type);
            const isLoan = ['loan', 'loan_account'].includes(acc.account_type);

            return (
              <Card
                key={acc.id}
                className="p-5 border-slate-800 bg-slate-900/80 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-slate-800/80 border border-white/5">
                        {getAccountIcon(acc.account_type)}
                      </div>
                      <div>
                        <h4 className="font-semibold text-white text-sm line-clamp-1">{acc.name}</h4>
                        <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                          <span>{acc.institution_name || 'Manual'}</span>
                          {acc.masked_identifier && (
                            <>
                              <span>•</span>
                              <span className="font-mono text-[11px] text-slate-400">{acc.masked_identifier}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    {getStatusBadge(acc.status)}
                  </div>

                  {/* Primary Balances Display */}
                  <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-2">
                    {isCard ? (
                      <>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">Outstanding Due</span>
                          <span className="font-bold text-rose-400 tabular-nums">
                            {formatINR(Number(acc.outstanding_liability || '0'))}
                          </span>
                        </div>
                        {acc.balances?.available_credit && (
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-400">Available Credit</span>
                            <span className="font-semibold text-emerald-400 tabular-nums">
                              {formatINR(Number(acc.balances.available_credit))}
                            </span>
                          </div>
                        )}
                        {acc.balances?.due_date && (
                          <div className="flex items-center justify-between text-xs text-slate-500">
                            <span>Payment Due</span>
                            <span className="flex items-center gap-1 text-slate-400">
                              <Clock size={12} />
                              {acc.balances.due_date}
                            </span>
                          </div>
                        )}
                      </>
                    ) : isLoan ? (
                      <>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">Outstanding Principal</span>
                          <span className="font-bold text-rose-400 tabular-nums">
                            {formatINR(Number(acc.outstanding_liability || '0'))}
                          </span>
                        </div>
                        {acc.balances?.repayment_amount && (
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-400">Monthly EMI</span>
                            <span className="font-semibold text-amber-300 tabular-nums">
                              {formatINR(Number(acc.balances.repayment_amount))}
                            </span>
                          </div>
                        )}
                        {acc.balances?.interest_rate != null && (
                          <div className="flex items-center justify-between text-xs text-slate-500">
                            <span>Interest Rate</span>
                            <span className="text-slate-300">{acc.balances.interest_rate}% p.a.</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">Book Balance</span>
                          <span className="font-bold text-white text-base tabular-nums">
                            {formatINR(Number(acc.current_book_balance || '0'))}
                          </span>
                        </div>
                        {acc.available_balance && acc.available_balance !== acc.current_book_balance && (
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-slate-500">Available Balance</span>
                            <span className="font-semibold text-emerald-400 tabular-nums">
                              {formatINR(Number(acc.available_balance))}
                            </span>
                          </div>
                        )}
                        {acc.provider_reported_balance && (
                          <div className="flex items-center justify-between text-xs text-slate-500">
                            <span>Provider Feed</span>
                            <span className="tabular-nums text-slate-400">
                              {formatINR(Number(acc.provider_reported_balance))}
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Card Footer Actions */}
                <div className="mt-5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
                  <button
                    onClick={() => openAccountDetails(acc)}
                    className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 transition-colors"
                  >
                    <span>Details & History</span>
                    <History size={13} />
                  </button>

                  <div className="flex items-center gap-2">
                    {acc.status === 'active' && (
                      <button
                        onClick={() => handleArchive(acc.id)}
                        title="Archive account"
                        className="text-slate-400 hover:text-amber-400 p-1 transition-colors"
                      >
                        <Archive size={14} />
                      </button>
                    )}
                    {acc.status === 'archived' && (
                      <button
                        onClick={() => handleRestore(acc.id)}
                        title="Restore account"
                        className="text-slate-400 hover:text-emerald-400 p-1 transition-colors"
                      >
                        <RotateCcw size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Account Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Financial Account"
        description="Register a new bank account, credit card, wallet, or loan container."
        size="lg"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Account Name *</label>
              <Input
                required
                placeholder="e.g. HDFC Salary Savings"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-slate-900 border-slate-800 text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Account Type *</label>
              <select
                value={formData.account_type}
                onChange={(e) => setFormData({ ...formData, account_type: e.target.value as AccountType })}
                className="w-full h-10 px-3 rounded-md bg-slate-900 border border-slate-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <optgroup label="Personal / Household">
                  <option value="savings">Savings Account</option>
                  <option value="salary">Salary Account</option>
                  <option value="current">Current Account</option>
                  <option value="credit_card">Credit Card</option>
                  <option value="digital_wallet">Digital Wallet (Paytm, etc.)</option>
                  <option value="cash">Cash in Hand</option>
                  <option value="fixed_deposit">Fixed Deposit</option>
                  <option value="recurring_deposit">Recurring Deposit</option>
                  <option value="loan">Loan Account</option>
                  <option value="investment">Investment / Demat</option>
                  <option value="other">Other</option>
                </optgroup>
                <optgroup label="Small Business">
                  <option value="business_bank">Business Bank Account</option>
                  <option value="business_current">Business Current Account</option>
                  <option value="business_credit_card">Business Credit Card</option>
                  <option value="petty_cash">Petty Cash</option>
                  <option value="loan_account">Commercial Loan</option>
                  <option value="other_business">Other Business</option>
                </optgroup>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Institution Name</label>
              <Input
                placeholder="e.g. HDFC Bank, SBI"
                value={formData.institution_name || ''}
                onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                className="bg-slate-900 border-slate-800 text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Masked Number</label>
              <Input
                placeholder="e.g. ••••4321"
                value={formData.masked_identifier || ''}
                onChange={(e) => setFormData({ ...formData, masked_identifier: e.target.value })}
                className="bg-slate-900 border-slate-800 text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Currency</label>
              <Input
                disabled
                value="INR"
                className="bg-slate-900 border-slate-800 text-slate-400"
              />
            </div>
          </div>

          {/* Conditional Fields based on Account Type */}
          {['credit_card', 'business_credit_card'].includes(formData.account_type) ? (
            <div className="p-3.5 rounded-xl bg-slate-900/90 border border-amber-500/20 space-y-3">
              <h5 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Credit Card Parameters</h5>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Credit Limit</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="200000.00"
                    value={formData.credit_limit || ''}
                    onChange={(e) => setFormData({ ...formData, credit_limit: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Current Outstanding</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="12500.00"
                    value={formData.outstanding_liability || ''}
                    onChange={(e) => setFormData({ ...formData, outstanding_liability: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Statement Due Date</label>
                  <Input
                    type="date"
                    value={formData.due_date || ''}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
              </div>
            </div>
          ) : ['loan', 'loan_account'].includes(formData.account_type) ? (
            <div className="p-3.5 rounded-xl bg-slate-900/90 border border-rose-500/20 space-y-3">
              <h5 className="text-xs font-bold text-rose-400 uppercase tracking-wider">Loan & EMI Parameters</h5>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Original Principal</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="5000000.00"
                    value={formData.original_principal || ''}
                    onChange={(e) => setFormData({ ...formData, original_principal: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Outstanding Principal</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="4750000.00"
                    value={formData.outstanding_principal || ''}
                    onChange={(e) => setFormData({ ...formData, outstanding_principal: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Interest Rate (% p.a.)</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="8.50"
                    value={formData.interest_rate !== undefined ? String(formData.interest_rate) : ''}
                    onChange={(e) => setFormData({ ...formData, interest_rate: e.target.value ? parseFloat(e.target.value) : undefined })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Monthly EMI Amount</label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="42500.00"
                    value={formData.repayment_amount || ''}
                    onChange={(e) => setFormData({ ...formData, repayment_amount: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Next EMI Due Date</label>
                  <Input
                    type="date"
                    value={formData.loan_due_date || ''}
                    onChange={(e) => setFormData({ ...formData, loan_due_date: e.target.value })}
                    className="bg-slate-950 border-slate-800 text-white"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Opening Balance</label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={formData.opening_balance || ''}
                  onChange={(e) => setFormData({ ...formData, opening_balance: e.target.value })}
                  className="bg-slate-900 border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Opening Date</label>
                <Input
                  type="date"
                  value={formData.opening_date || ''}
                  onChange={(e) => setFormData({ ...formData, opening_date: e.target.value })}
                  className="bg-slate-900 border-slate-800 text-white"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Notes / Description</label>
            <Input
              placeholder="e.g. Primary household salary account with ICICI"
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="bg-slate-900 border-slate-800 text-white"
            />
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddModalOpen(false)}
              className="border-slate-800 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              {isSubmitting ? 'Creating...' : 'Create Account'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Account Details & Balance History Modal */}
      {selectedAccount && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          title={
            <div className="flex items-center gap-3">
              <span>{selectedAccount.name}</span>
              {getStatusBadge(selectedAccount.status)}
            </div>
          }
          description={`${selectedAccount.institution_name || 'Manual'} • ${selectedAccount.account_type.toUpperCase()} • ${selectedAccount.currency}`}
          size="lg"
        >
          <div className="space-y-6">
            {/* Balance Overview Breakdown */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <span className="text-xs text-slate-400">Current Book Balance</span>
                <div className="text-lg font-bold text-white tabular-nums">
                  {formatINR(Number(selectedAccount.current_book_balance || '0'))}
                </div>
              </div>
              {selectedAccount.available_balance && (
                <div>
                  <span className="text-xs text-slate-400">Available Funds</span>
                  <div className="text-lg font-bold text-emerald-400 tabular-nums">
                    {formatINR(Number(selectedAccount.available_balance))}
                  </div>
                </div>
              )}
              {selectedAccount.outstanding_liability && (
                <div>
                  <span className="text-xs text-slate-400">Outstanding Liability</span>
                  <div className="text-lg font-bold text-rose-400 tabular-nums">
                    {formatINR(Number(selectedAccount.outstanding_liability))}
                  </div>
                </div>
              )}
              {selectedAccount.balances?.credit_limit && (
                <div>
                  <span className="text-xs text-slate-400">Credit Limit</span>
                  <div className="text-base font-semibold text-amber-300 tabular-nums">
                    {formatINR(Number(selectedAccount.balances.credit_limit))}
                  </div>
                </div>
              )}
              {selectedAccount.balances?.repayment_amount && (
                <div>
                  <span className="text-xs text-slate-400">Monthly EMI</span>
                  <div className="text-base font-semibold text-slate-200 tabular-nums">
                    {formatINR(Number(selectedAccount.balances.repayment_amount))}
                  </div>
                </div>
              )}
              {selectedAccount.provider_reported_balance && (
                <div>
                  <span className="text-xs text-slate-400">Provider Feed</span>
                  <div className="text-base font-semibold text-slate-300 tabular-nums">
                    {formatINR(Number(selectedAccount.provider_reported_balance))}
                  </div>
                  {selectedAccount.provider_reported_at && (
                    <span className="text-[10px] text-slate-500">
                      Synced {new Date(selectedAccount.provider_reported_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Snapshot History Table */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <History size={14} className="text-indigo-400" />
                  Point-In-Time Balance Snapshots
                </h4>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsSnapshotModalOpen(true)}
                  className="text-xs h-7 border-slate-700 text-slate-300 hover:text-white"
                >
                  <Plus size={13} className="mr-1" />
                  Record Snapshot
                </Button>
              </div>

              {historyLoading ? (
                <div className="py-8 text-center text-slate-500 text-xs">
                  <RefreshCw className="animate-spin mx-auto mb-1.5" size={16} />
                  Loading snapshot audit trail...
                </div>
              ) : balanceHistory.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-4">No snapshots recorded yet.</p>
              ) : (
                <div className="max-h-60 overflow-y-auto rounded-lg border border-slate-800">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2 px-3">Date</th>
                        <th className="py-2 px-3">Type</th>
                        <th className="py-2 px-3 text-right">Amount</th>
                        <th className="py-2 px-3">Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                      {balanceHistory.map((snap) => (
                        <tr key={snap.id} className="hover:bg-slate-900/50">
                          <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">
                            {new Date(snap.effective_at).toLocaleDateString()}
                          </td>
                          <td className="py-2 px-3 capitalize text-slate-300">
                            {snap.balance_type.replace('_', ' ')}
                          </td>
                          <td className="py-2 px-3 text-right font-semibold text-white tabular-nums">
                            {formatINR(Number(snap.balance_amount))}
                          </td>
                          <td className="py-2 px-3 text-slate-500 font-mono text-[11px]">
                            {snap.source}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Lifecycle Controls */}
            <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {selectedAccount.status === 'active' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleArchive(selectedAccount.id)}
                    className="text-xs border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                  >
                    <Archive size={14} className="mr-1.5" />
                    Archive Account
                  </Button>
                )}
                {selectedAccount.status === 'archived' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRestore(selectedAccount.id)}
                    className="text-xs border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                  >
                    <RotateCcw size={14} className="mr-1.5" />
                    Restore Account
                  </Button>
                )}
                {selectedAccount.status !== 'closed' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsCloseModalOpen(true)}
                    className="text-xs border-rose-500/30 text-rose-400 hover:bg-rose-500/10"
                  >
                    <XCircle size={14} className="mr-1.5" />
                    Close Account
                  </Button>
                )}
              </div>

              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsDetailModalOpen(false)}
                className="border-slate-800 text-slate-400"
              >
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Record Balance Snapshot Modal */}
      <Modal
        isOpen={isSnapshotModalOpen}
        onClose={() => setIsSnapshotModalOpen(false)}
        title="Record Balance Snapshot"
        description="Save an immutable point-in-time balance record for reconciliation."
        size="sm"
      >
        <form onSubmit={handleRecordSnapshotSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Balance Type</label>
            <select
              value={snapshotData.balance_type}
              onChange={(e) => setSnapshotData({ ...snapshotData, balance_type: e.target.value })}
              className="w-full h-10 px-3 rounded-md bg-slate-900 border border-slate-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="provider_reported">Provider Reported (Bank Statement/Feed)</option>
              <option value="available">Available Balance</option>
              <option value="book">Book Balance</option>
              <option value="liability">Outstanding Liability</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Exact Balance Amount *</label>
            <Input
              required
              type="number"
              step="0.01"
              placeholder="e.g. 54200.75"
              value={snapshotData.balance_amount}
              onChange={(e) => setSnapshotData({ ...snapshotData, balance_amount: e.target.value })}
              className="bg-slate-900 border-slate-800 text-white"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Source / Reference</label>
            <Input
              placeholder="e.g. Bank statement PDF reconciliation"
              value={snapshotData.source_reference || ''}
              onChange={(e) => setSnapshotData({ ...snapshotData, source_reference: e.target.value })}
              className="bg-slate-900 border-slate-800 text-white"
            />
          </div>
          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsSnapshotModalOpen(false)}
              className="border-slate-800 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              {isSubmitting ? 'Recording...' : 'Record Snapshot'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Close Account Modal */}
      <Modal
        isOpen={isCloseModalOpen}
        onClose={() => setIsCloseModalOpen(false)}
        title="Close Financial Account"
        description="Permanently close this account. It will preserve all historical transactions and records."
        size="sm"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>Closed accounts cannot accept new transactions. Closing date cannot precede the account opening date.</span>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Closing Effective Date</label>
            <Input
              type="date"
              value={closingDate}
              onChange={(e) => setClosingDate(e.target.value)}
              className="bg-slate-900 border-slate-800 text-white"
            />
          </div>
          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCloseModalOpen(false)}
              className="border-slate-800 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleClose}
              disabled={isSubmitting}
              className="bg-rose-600 hover:bg-rose-500 text-white"
            >
              {isSubmitting ? 'Closing...' : 'Confirm Account Closure'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
