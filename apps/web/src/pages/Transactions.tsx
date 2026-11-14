import React, { useEffect, useState, useMemo } from 'react';
import useTransactionStore from '@/store/useTransactionStore';
import useAccountStore from '@/store/useAccountStore';
import {
  ArrowDownLeft,
  ArrowUpRight,
  ArrowLeftRight,
  RotateCcw,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  XCircle,
  AlertCircle,
  Plus,
  History,
  Sparkles,
  Receipt,
  Undo2,
  CornerDownLeft,
} from 'lucide-react';
import { formatINR, formatDateINR } from '@arthsavora/utilities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { toast } from 'sonner';
import type {
  TransactionResponse,
  TransactionCreateRequest,
  TransferCreateRequest,
  TransactionType,
  TransactionDirection,
} from '@arthsavora/contracts';

export default function Transactions() {
  const {
    transactions,
    total,
    loading,
    historyLoading,
    activeHistory,
    fetchTransactions,
    createTransaction,
    createTransfer,
    postTransaction,
    cancelTransaction,
    reverseTransaction,
    refundTransaction,
    fetchHistory,
  } = useTransactionStore();

  const { accounts, fetchAccounts } = useAccountStore();

  // Filters State
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [directionFilter, setDirectionFilter] = useState('all');
  const [accountFilter, setAccountFilter] = useState('all');
  const [page, setPage] = useState(1);

  // Modals State
  const [isTxModalOpen, setIsTxModalOpen] = useState(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [isReverseModalOpen, setIsReverseModalOpen] = useState(false);
  const [isRefundModalOpen, setIsRefundModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<TransactionResponse | null>(null);

  // Forms State
  const [txForm, setTxForm] = useState<{
    account_id: string;
    amount: string;
    transaction_type: TransactionType | string;
    direction: TransactionDirection | 'auto';
    transaction_date: string;
    description: string;
    merchant_name: string;
    status: 'posted' | 'pending';
    is_ai_predicted: boolean;
    ai_confidence: string;
  }>({
    account_id: '',
    amount: '',
    transaction_type: 'expense',
    direction: 'auto',
    transaction_date: new Date().toISOString().split('T')[0],
    description: '',
    merchant_name: '',
    status: 'posted',
    is_ai_predicted: false,
    ai_confidence: '0.85',
  });

  const [transferForm, setTransferForm] = useState<{
    source_account_id: string;
    destination_account_id: string;
    amount: string;
    transfer_date: string;
    description: string;
  }>({
    source_account_id: '',
    destination_account_id: '',
    amount: '',
    transfer_date: new Date().toISOString().split('T')[0],
    description: '',
  });

  const [reverseReason, setReverseReason] = useState('');
  const [refundAmount, setRefundAmount] = useState('');
  const [refundDescription, setRefundDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  useEffect(() => {
    fetchTransactions({
      page,
      search: search.trim() || undefined,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      direction: directionFilter !== 'all' ? directionFilter : undefined,
      accountId: accountFilter !== 'all' ? accountFilter : undefined,
    });
  }, [fetchTransactions, page, search, statusFilter, directionFilter, accountFilter]);

  // Derived KPIs
  const stats = useMemo(() => {
    let inflowPaise = 0;
    let outflowPaise = 0;
    let pendingCount = 0;
    transactions.forEach((tx) => {
      if (tx.status === 'pending') pendingCount++;
      if (tx.status === 'posted') {
        if (tx.direction === 'inflow') inflowPaise += tx.amount_paise;
        if (tx.direction === 'outflow') outflowPaise += tx.amount_paise;
      }
    });
    return {
      inflow: inflowPaise / 100,
      outflow: outflowPaise / 100,
      pending: pendingCount,
      totalCount: total,
    };
  }, [transactions, total]);

  const handleCreateTx = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!txForm.account_id || !txForm.amount || !txForm.description) {
      toast.error('Please fill required fields (Account, Amount, Description)');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: TransactionCreateRequest = {
        account_id: txForm.account_id,
        amount: txForm.amount,
        transaction_type: txForm.transaction_type,
        direction: txForm.direction !== 'auto' ? txForm.direction : undefined,
        transaction_date: txForm.transaction_date,
        description: txForm.description.trim(),
        merchant_name: txForm.merchant_name.trim() || undefined,
        status: txForm.status,
        is_ai_predicted: txForm.is_ai_predicted,
        ai_confidence: txForm.is_ai_predicted ? parseFloat(txForm.ai_confidence) : undefined,
      };
      const res = await createTransaction(payload);
      if (res.success) {
        toast.success('Transaction recorded successfully');
        setIsTxModalOpen(false);
        setTxForm({
          account_id: accounts[0]?.id || '',
          amount: '',
          transaction_type: 'expense',
          direction: 'auto',
          transaction_date: new Date().toISOString().split('T')[0],
          description: '',
          merchant_name: '',
          status: 'posted',
          is_ai_predicted: false,
          ai_confidence: '0.85',
        });
      } else {
        toast.error(res.error || 'Failed to record transaction');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transferForm.source_account_id || !transferForm.destination_account_id || !transferForm.amount) {
      toast.error('Please specify source, destination, and amount');
      return;
    }
    if (transferForm.source_account_id === transferForm.destination_account_id) {
      toast.error('Source and destination accounts must be distinct');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: TransferCreateRequest = {
        source_account_id: transferForm.source_account_id,
        destination_account_id: transferForm.destination_account_id,
        amount: transferForm.amount,
        transfer_date: transferForm.transfer_date,
        description: transferForm.description.trim() || undefined,
      };
      const res = await createTransfer(payload);
      if (res.success) {
        toast.success('Transfer executed successfully');
        setIsTransferModalOpen(false);
        setTransferForm({
          source_account_id: '',
          destination_account_id: '',
          amount: '',
          transfer_date: new Date().toISOString().split('T')[0],
          description: '',
        });
      } else {
        toast.error(res.error || 'Failed to execute transfer');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePost = async (tx: TransactionResponse) => {
    const res = await postTransaction(tx.id);
    if (res.success) {
      toast.success('Transaction posted');
    } else {
      toast.error(res.error || 'Failed to post transaction');
    }
  };

  const handleCancel = async (tx: TransactionResponse) => {
    const res = await cancelTransaction(tx.id, { cancellation_reason: 'User cancelled' });
    if (res.success) {
      toast.success('Pending transaction cancelled');
    } else {
      toast.error(res.error || 'Failed to cancel transaction');
    }
  };

  const handleReverse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTx || !reverseReason.trim()) return;
    setIsSubmitting(true);
    try {
      const res = await reverseTransaction(selectedTx.id, { reason: reverseReason.trim() });
      if (res.success) {
        toast.success('Compensating reversal recorded');
        setIsReverseModalOpen(false);
        setReverseReason('');
        setSelectedTx(null);
      } else {
        toast.error(res.error || 'Failed to reverse transaction');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTx || !refundAmount) return;
    setIsSubmitting(true);
    try {
      const res = await refundTransaction(selectedTx.id, {
        refund_amount: refundAmount,
        description: refundDescription.trim() || undefined,
      });
      if (res.success) {
        toast.success('Refund recorded successfully');
        setIsRefundModalOpen(false);
        setRefundAmount('');
        setRefundDescription('');
        setSelectedTx(null);
      } else {
        toast.error(res.error || 'Failed to refund transaction');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const openHistory = async (tx: TransactionResponse) => {
    setSelectedTx(tx);
    setIsHistoryModalOpen(true);
    await fetchHistory(tx.id);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Receipt className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            Financial Transactions
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Immutable operational journal with multi-source provenance, balance synchronization, and auditability.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex items-center gap-1.5"
            onClick={() => setIsTransferModalOpen(true)}
          >
            <ArrowLeftRight className="h-4 w-4 text-sky-600 dark:text-sky-400" />
            Transfer
          </Button>
          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
            onClick={() => {
              if (accounts.length > 0 && !txForm.account_id) {
                setTxForm((f) => ({ ...f, account_id: accounts[0].id }));
              }
              setIsTxModalOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            New Transaction
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Total Entries</p>
            <Receipt className="h-4 w-4 text-slate-400" />
          </div>
          <p className="text-2xl font-bold mt-2 text-slate-900 dark:text-slate-100">{stats.totalCount}</p>
          <p className="text-xs text-slate-400 mt-1">Across all workspace accounts</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Posted Inflow</p>
            <ArrowDownLeft className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-emerald-600 dark:text-emerald-400">{formatINR(stats.inflow)}</p>
          <p className="text-xs text-slate-400 mt-1">Income & credits on page</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Posted Outflow</p>
            <ArrowUpRight className="h-4 w-4 text-rose-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-rose-600 dark:text-rose-400">{formatINR(stats.outflow)}</p>
          <p className="text-xs text-slate-400 mt-1">Expenses & debt on page</p>
        </Card>

        <Card className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Pending Holds</p>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-amber-600 dark:text-amber-400">{stats.pending}</p>
          <p className="text-xs text-slate-400 mt-1">Unsettled authorizations</p>
        </Card>
      </div>

      {/* Filters Toolbar */}
      <Card className="p-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search narrative, merchant..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="pl-9"
            />
          </div>

          <select
            className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
            value={directionFilter}
            onChange={(e) => {
              setDirectionFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="all">All Directions</option>
            <option value="inflow">Inflow (Credits/Income)</option>
            <option value="outflow">Outflow (Debits/Expenses)</option>
            <option value="neutral">Neutral (Transfers)</option>
          </select>

          <select
            className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="all">All Statuses</option>
            <option value="posted">Posted</option>
            <option value="pending">Pending</option>
            <option value="reversed">Reversed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <select
            className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
            value={accountFilter}
            onChange={(e) => {
              setAccountFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="all">All Accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.currency})
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Transaction Table */}
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex items-center justify-center gap-2">
            <RefreshCw className="h-5 w-5 animate-spin" />
            Loading financial journal...
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Receipt className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium text-slate-600 dark:text-slate-300">No transactions recorded</p>
            <p className="text-xs mt-1">Record a new transaction or execute an account transfer to populate the journal.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Narrative & Merchant</th>
                  <th className="py-3 px-4">Account</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {transactions.map((tx) => {
                  const acct = accounts.find((a) => a.id === tx.account_id);
                  const isOutflow = tx.direction === 'outflow';
                  const isInflow = tx.direction === 'inflow';
                  const numAmt = parseFloat(tx.amount);

                  return (
                    <tr key={tx.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500 dark:text-slate-400">
                        {formatDateINR(tx.transaction_date)}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          {tx.description}
                          {tx.is_ai_predicted && (
                            <Badge variant="info" className="text-[10px] px-1 py-0 text-indigo-600 border-indigo-200 flex items-center gap-0.5">
                              <Sparkles className="h-2.5 w-2.5" />
                              AI {(tx.ai_confidence ? (tx.ai_confidence * 100).toFixed(0) : '85')}%
                            </Badge>
                          )}
                          {tx.transfer_id && (
                            <Badge variant="neutral" className="text-[10px] px-1 py-0 text-sky-600 border-sky-200">
                              Transfer
                            </Badge>
                          )}
                        </div>
                        {tx.merchant_name && (
                          <div className="text-xs text-slate-400">{tx.merchant_name}</div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-600 dark:text-slate-300">
                        {acct ? acct.name : 'Unknown Account'}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="capitalize text-xs font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {tx.transaction_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-right font-semibold">
                        <span
                          className={
                            isInflow
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : isOutflow
                              ? 'text-rose-600 dark:text-rose-400'
                              : 'text-slate-600 dark:text-slate-300'
                          }
                        >
                          {isInflow ? '+' : isOutflow ? '-' : ''}
                          {formatINR(numAmt)}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {tx.status === 'posted' && (
                          <Badge className="bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800 gap-1">
                            <CheckCircle2 className="h-3 w-3" /> Posted
                          </Badge>
                        )}
                        {tx.status === 'pending' && (
                          <Badge className="bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800 gap-1">
                            <Clock className="h-3 w-3" /> Pending
                          </Badge>
                        )}
                        {tx.status === 'reversed' && (
                          <Badge className="bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800 gap-1">
                            <RotateCcw className="h-3 w-3" /> Reversed
                          </Badge>
                        )}
                        {tx.status === 'cancelled' && (
                          <Badge className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 gap-1">
                            <XCircle className="h-3 w-3" /> Cancelled
                          </Badge>
                        )}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          {tx.status === 'pending' && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs text-emerald-600 hover:text-emerald-700"
                                onClick={() => handlePost(tx)}
                              >
                                Clear
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs text-rose-600 hover:text-rose-700"
                                onClick={() => handleCancel(tx)}
                              >
                                Cancel
                              </Button>
                            </>
                          )}
                          {tx.status === 'posted' && (
                            <>
                              {isOutflow && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 text-xs text-sky-600 hover:text-sky-700 px-2"
                                  title="Issue Partial or Full Refund"
                                  onClick={() => {
                                    setSelectedTx(tx);
                                    setRefundAmount(tx.amount);
                                    setIsRefundModalOpen(true);
                                  }}
                                >
                                  Refund
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs text-purple-600 hover:text-purple-700 px-2"
                                title="Issue Compensating Reversal"
                                onClick={() => {
                                  setSelectedTx(tx);
                                  setIsReverseModalOpen(true);
                                }}
                              >
                                Reverse
                              </Button>
                            </>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs text-slate-400 hover:text-slate-600 px-2"
                            title="View Audit Trail"
                            onClick={() => openHistory(tx)}
                          >
                            <History className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* New Transaction Modal */}
      <Modal
        isOpen={isTxModalOpen}
        onClose={() => setIsTxModalOpen(false)}
        title="Record Financial Transaction"
      >
        <form onSubmit={handleCreateTx} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Account *
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
              value={txForm.account_id}
              onChange={(e) => setTxForm({ ...txForm, account_id: e.target.value })}
              required
            >
              <option value="">Select Account</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.account_type} - {a.currency})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Amount (₹) *
              </label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                value={txForm.amount}
                onChange={(e) => setTxForm({ ...txForm, amount: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Date *
              </label>
              <Input
                type="date"
                value={txForm.transaction_date}
                onChange={(e) => setTxForm({ ...txForm, transaction_date: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Transaction Type *
              </label>
              <select
                className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
                value={txForm.transaction_type}
                onChange={(e) => setTxForm({ ...txForm, transaction_type: e.target.value })}
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
                <option value="deposit">Deposit</option>
                <option value="withdrawal">Withdrawal</option>
                <option value="credit_card_purchase">Credit Card Purchase</option>
                <option value="credit_card_payment">Credit Card Payment</option>
                <option value="loan_principal_repayment">Loan Repayment</option>
                <option value="bank_fee">Bank Fee</option>
                <option value="interest_income">Interest Income</option>
                <option value="cash_transaction">Cash Movement</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Status *
              </label>
              <select
                className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
                value={txForm.status}
                onChange={(e) => setTxForm({ ...txForm, status: e.target.value as 'posted' | 'pending' })}
              >
                <option value="posted">Posted (Directly syncs balance)</option>
                <option value="pending">Pending (Reserves hold)</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="tx-description" className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Description / Narrative *
            </label>
            <Input
              id="tx-description"
              placeholder="e.g. AWS Cloud Hosting Invoice"
              value={txForm.description}
              onChange={(e) => setTxForm({ ...txForm, description: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Merchant / Counterparty
            </label>
            <Input
              placeholder="e.g. Amazon Web Services Inc."
              value={txForm.merchant_name}
              onChange={(e) => setTxForm({ ...txForm, merchant_name: e.target.value })}
            />
          </div>

          <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
            <input
              type="checkbox"
              id="ai_predicted_check"
              checked={txForm.is_ai_predicted}
              onChange={(e) => setTxForm({ ...txForm, is_ai_predicted: e.target.checked })}
              className="rounded border-slate-300"
            />
            <label htmlFor="ai_predicted_check" className="text-xs text-slate-600 dark:text-slate-400">
              Flag as AI-Categorized prediction
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => setIsTxModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              {isSubmitting ? 'Recording...' : 'Record Transaction'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Internal Transfer Modal */}
      <Modal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        title="Execute Internal Account Transfer"
      >
        <form onSubmit={handleCreateTransfer} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              From Source Account (Outflow) *
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
              value={transferForm.source_account_id}
              onChange={(e) => setTransferForm({ ...transferForm, source_account_id: e.target.value })}
              required
            >
              <option value="">Select Source Account</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({formatINR(parseFloat(a.current_book_balance))})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              To Destination Account (Inflow) *
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 text-sm text-slate-900 dark:text-slate-100"
              value={transferForm.destination_account_id}
              onChange={(e) => setTransferForm({ ...transferForm, destination_account_id: e.target.value })}
              required
            >
              <option value="">Select Destination Account</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.account_type} - {formatINR(parseFloat(a.current_book_balance))})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Amount (₹) *
              </label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                value={transferForm.amount}
                onChange={(e) => setTransferForm({ ...transferForm, amount: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Transfer Date *
              </label>
              <Input
                type="date"
                value={transferForm.transfer_date}
                onChange={(e) => setTransferForm({ ...transferForm, transfer_date: e.target.value })}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Description Note
            </label>
            <Input
              placeholder="e.g. Credit Card Payment from Savings"
              value={transferForm.description}
              onChange={(e) => setTransferForm({ ...transferForm, description: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => setIsTransferModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-sky-600 hover:bg-sky-700 text-white">
              {isSubmitting ? 'Transferring...' : 'Execute Transfer'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Formal Reversal Modal */}
      <Modal
        isOpen={isReverseModalOpen}
        onClose={() => {
          setIsReverseModalOpen(false);
          setSelectedTx(null);
        }}
        title="Formal Transaction Reversal"
      >
        <form onSubmit={handleReverse} className="space-y-4">
          <div className="p-3 bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800 rounded-md text-xs text-purple-800 dark:text-purple-300">
            <p className="font-semibold mb-1">Auditable Accounting Invariant</p>
            Posted financial facts cannot be edited or deleted. Reversing creates a compensating reversal entry with inverted direction, restoring account book balance.
          </div>

          {selectedTx && (
            <div className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
              <div><span className="font-medium">Original Description:</span> {selectedTx.description}</div>
              <div><span className="font-medium">Amount:</span> {formatINR(parseFloat(selectedTx.amount))}</div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Reason for Reversal *
            </label>
            <Input
              placeholder="e.g. Duplicate bank charge, incorrect voucher entry"
              value={reverseReason}
              onChange={(e) => setReverseReason(e.target.value)}
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => setIsReverseModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-purple-600 hover:bg-purple-700 text-white">
              {isSubmitting ? 'Reversing...' : 'Confirm Reversal'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Partial / Full Refund Modal */}
      <Modal
        isOpen={isRefundModalOpen}
        onClose={() => {
          setIsRefundModalOpen(false);
          setSelectedTx(null);
        }}
        title="Record Transaction Refund"
      >
        <form onSubmit={handleRefund} className="space-y-4">
          <div className="p-3 bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800 rounded-md text-xs text-sky-800 dark:text-sky-300">
            <p className="font-semibold mb-1">Cumulative Refund Bound</p>
            Refunds record an inflow linked to the original purchase. Total cumulative refunds cannot exceed the original transaction amount.
          </div>

          {selectedTx && (
            <div className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
              <div><span className="font-medium">Original Amount:</span> {formatINR(parseFloat(selectedTx.amount))}</div>
              <div><span className="font-medium">Original Date:</span> {formatDateINR(selectedTx.transaction_date)}</div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Refund Amount (₹) *
            </label>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              value={refundAmount}
              onChange={(e) => setRefundAmount(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Refund Narrative Note
            </label>
            <Input
              placeholder="e.g. Return of damaged item"
              value={refundDescription}
              onChange={(e) => setRefundDescription(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => setIsRefundModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-sky-600 hover:bg-sky-700 text-white">
              {isSubmitting ? 'Recording...' : 'Record Refund'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Audit History Modal */}
      <Modal
        isOpen={isHistoryModalOpen}
        onClose={() => {
          setIsHistoryModalOpen(false);
          setSelectedTx(null);
        }}
        title="Transaction Audit History"
      >
        <div className="space-y-3">
          {historyLoading ? (
            <div className="p-6 text-center text-slate-400 flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Loading audit timeline...
            </div>
          ) : activeHistory.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-4">No audit logs found for this transaction.</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {activeHistory.map((h) => (
                <div
                  key={h.id}
                  className="p-3 rounded-md bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-xs"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">
                      {h.action.replace(/:/g, ' ')}
                    </span>
                    <span className="text-slate-400">{new Date(h.timestamp).toLocaleString('en-IN')}</span>
                  </div>
                  <pre className="text-[11px] text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/60 p-2 rounded overflow-x-auto">
                    {JSON.stringify(h.details, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
