import React, { useEffect, useState } from 'react';
import { useLedgerStore } from '../store/useLedgerStore';
import { PageContainer } from '../components/layout/PageContainer';
import { SectionHeader } from '../components/layout/SectionHeader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Modal } from '../components/ui/modal';
import { Alert } from '../components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { FinancialAmount } from '../components/ui/financial-amount';
import {
  JournalEntryCreateRequest,
  JournalEntryResponse,
  JournalLineCreateRequest,
  LedgerAccountCreateRequest,
  LedgerAccountResponse,
} from '@arthsavora/contracts';

export const Ledger: React.FC = () => {
  const {
    accounts,
    journals,
    trialBalance,
    selectedJournal,
    isLoading,
    error,
    fetchAccounts,
    fetchJournals,
    fetchTrialBalance,
    getJournal,
    createJournal,
    postJournal,
    reverseJournal,
    createAccount,
    setSelectedJournal,
    clearError,
  } = useLedgerStore();

  const [activeTab, setActiveTab] = useState<'journals' | 'coa' | 'trial_balance'>('journals');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [coaFilter, setCoaFilter] = useState<string>('all');

  // Modals state
  const [isCreateJournalOpen, setIsCreateJournalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isReverseModalOpen, setIsReverseModalOpen] = useState(false);
  const [isCreateAccountOpen, setIsCreateAccountOpen] = useState(false);

  // Journal creation form state
  const [journalDate, setJournalDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [journalDesc, setJournalDesc] = useState<string>('');
  const [journalLines, setJournalLines] = useState<JournalLineCreateRequest[]>([
    { ledger_account_id: '', entry_type: 'debit', amount: '' },
    { ledger_account_id: '', entry_type: 'credit', amount: '' },
  ]);

  // Reversal form state
  const [reversalReason, setReversalReason] = useState<string>('');
  const [reversingJournalId, setReversingJournalId] = useState<string | null>(null);

  // Account creation form state
  const [newAccountCode, setNewAccountCode] = useState<string>('');
  const [newAccountName, setNewAccountName] = useState<string>('');
  const [newAccountType, setNewAccountType] = useState<string>('expense');
  const [newAccountSubtype, setNewAccountSubtype] = useState<string>('');
  const [newAccountDesc, setNewAccountDesc] = useState<string>('');

  useEffect(() => {
    fetchAccounts();
    fetchJournals();
  }, []);

  useEffect(() => {
    if (activeTab === 'trial_balance') {
      fetchTrialBalance();
    }
  }, [activeTab]);

  // Compute live debits and credits for draft creation modal
  const liveTotalDebits = journalLines
    .filter((l) => l.entry_type === 'debit' && l.amount && !isNaN(Number(l.amount)))
    .reduce((sum, l) => sum + Number(l.amount), 0);

  const liveTotalCredits = journalLines
    .filter((l) => l.entry_type === 'credit' && l.amount && !isNaN(Number(l.amount)))
    .reduce((sum, l) => sum + Number(l.amount), 0);

  const isLiveDraftBalanced =
    liveTotalDebits > 0 &&
    Math.abs(liveTotalDebits - liveTotalCredits) < 0.0001 &&
    journalLines.length >= 2;

  const handleAddLine = () => {
    setJournalLines([
      ...journalLines,
      { ledger_account_id: accounts[0]?.id || '', entry_type: 'debit', amount: '' },
    ]);
  };

  const handleRemoveLine = (index: number) => {
    if (journalLines.length <= 2) return;
    setJournalLines(journalLines.filter((_, i) => i !== index));
  };

  const handleLineChange = (index: number, field: keyof JournalLineCreateRequest, value: any) => {
    const updated = [...journalLines];
    updated[index] = { ...updated[index], [field]: value };
    setJournalLines(updated);
  };

  const handleSaveDraftJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!journalDesc) return;

    try {
      const payload: JournalEntryCreateRequest = {
        entry_date: journalDate,
        description: journalDesc,
        source_type: 'manual',
        lines: journalLines,
      };
      await createJournal(payload);
      setIsCreateJournalOpen(false);
      setJournalDesc('');
      setJournalLines([
        { ledger_account_id: accounts[0]?.id || '', entry_type: 'debit', amount: '' },
        { ledger_account_id: accounts[1]?.id || '', entry_type: 'credit', amount: '' },
      ]);
    } catch {
      // error set in store
    }
  };

  const handlePostJournal = async (journalId: string) => {
    try {
      await postJournal(journalId);
    } catch {
      // error handled in store
    }
  };

  const handleOpenReverse = (journalId: string) => {
    setReversingJournalId(journalId);
    setReversalReason('');
    setIsReverseModalOpen(true);
  };

  const handleConfirmReverse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reversingJournalId || !reversalReason) return;
    try {
      await reverseJournal(reversingJournalId, reversalReason);
      setIsReverseModalOpen(false);
      setReversingJournalId(null);
    } catch {
      // error handled in store
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAccountCode || !newAccountName) return;
    try {
      const payload: LedgerAccountCreateRequest = {
        code: newAccountCode,
        name: newAccountName,
        account_type: newAccountType,
        sub_type: newAccountSubtype || undefined,
        description: newAccountDesc || undefined,
      };
      await createAccount(payload);
      setIsCreateAccountOpen(false);
      setNewAccountCode('');
      setNewAccountName('');
      setNewAccountSubtype('');
      setNewAccountDesc('');
    } catch {
      // error handled in store
    }
  };

  const handleInspectJournal = async (journalId: string) => {
    await getJournal(journalId);
    setIsDetailModalOpen(true);
  };

  const filteredJournals = journals.filter((j) => {
    if (statusFilter !== 'all' && j.status !== statusFilter) return false;
    return true;
  });

  const filteredAccounts = accounts.filter((a) => {
    if (coaFilter !== 'all' && a.account_type !== coaFilter) return false;
    return true;
  });

  return (
    <PageContainer>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
        <SectionHeader
          title="General Ledger & Double-Entry Accounting"
          description="Authoritative double-entry ledger ensuring Total Debits == Total Credits with posting immutability."
        />
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setIsCreateAccountOpen(true)}
            aria-label="New Ledger Account"
          >
            + New Account
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              if (accounts.length >= 2) {
                setJournalLines([
                  { ledger_account_id: accounts[0].id, entry_type: 'debit', amount: '' },
                  { ledger_account_id: accounts[1].id, entry_type: 'credit', amount: '' },
                ]);
              }
              setIsCreateJournalOpen(true);
            }}
            aria-label="Record Journal Entry"
          >
            + Record Journal Entry
          </Button>
        </div>
      </div>

      {error && (
        <Alert
          variant="error"
          title="Accounting Invariant Error"
          onDismiss={clearError}
          className="mb-6"
        >
          {error}
        </Alert>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-neutral-200 dark:border-neutral-800 mb-6 gap-2">
        <button
          onClick={() => setActiveTab('journals')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'journals'
              ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400'
          }`}
        >
          General Journal
        </button>
        <button
          onClick={() => setActiveTab('coa')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'coa'
              ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400'
          }`}
        >
          Chart of Accounts
        </button>
        <button
          onClick={() => setActiveTab('trial_balance')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'trial_balance'
              ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400'
          }`}
        >
          Trial Balance
        </button>
      </div>

      {/* Tab 1: General Journal */}
      {activeTab === 'journals' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-sm border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-1.5 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
              >
                <option value="all">All Statuses</option>
                <option value="draft">Draft Entries</option>
                <option value="posted">Posted (Immutable)</option>
                <option value="reversed">Reversed</option>
              </select>
            </div>
            <span className="text-xs text-neutral-500">{filteredJournals.length} journal entries</span>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Entry #</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total Debit</TableHead>
                  <TableHead className="text-right">Total Credit</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJournals.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-neutral-500">
                      No journal entries found. Record your first balanced journal entry above.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredJournals.map((j) => (
                    <TableRow key={j.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
                      <TableCell className="font-mono font-medium text-primary-600 dark:text-primary-400">
                        {j.entry_number}
                      </TableCell>
                      <TableCell className="text-sm text-neutral-600 dark:text-neutral-400">
                        {j.entry_date}
                      </TableCell>
                      <TableCell className="font-medium text-neutral-900 dark:text-neutral-100 max-w-xs truncate">
                        {j.description}
                      </TableCell>
                      <TableCell className="text-xs text-neutral-500 uppercase tracking-wider">
                        {j.source_type}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            j.status === 'posted'
                              ? 'income'
                              : j.status === 'draft'
                              ? 'warning'
                              : 'neutral'
                          }
                        >
                          {j.status.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        <FinancialAmount amount={Number(j.total_debits)} currency="INR" />
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        <FinancialAmount amount={Number(j.total_credits)} currency="INR" />
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspectJournal(j.id)}
                        >
                          View Lines
                        </Button>
                        {j.status === 'draft' && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handlePostJournal(j.id)}
                          >
                            Post
                          </Button>
                        )}
                        {j.status === 'posted' && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleOpenReverse(j.id)}
                          >
                            Reverse
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Tab 2: Chart of Accounts */}
      {activeTab === 'coa' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Filter Classification:</span>
              <select
                value={coaFilter}
                onChange={(e) => setCoaFilter(e.target.value)}
                className="text-sm border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-1.5 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
              >
                <option value="all">All Classifications</option>
                <option value="asset">Assets (1000s)</option>
                <option value="liability">Liabilities (2000s)</option>
                <option value="equity">Equity (3000s)</option>
                <option value="revenue">Revenue (4000s)</option>
                <option value="expense">Expenses (5000s)</option>
              </select>
            </div>
            <span className="text-xs text-neutral-500">{filteredAccounts.length} ledger accounts</span>
          </div>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead>Normal Balance</TableHead>
                  <TableHead>Sub-Type</TableHead>
                  <TableHead>System Protected</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAccounts.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="font-mono font-bold text-neutral-900 dark:text-neutral-100">
                      {a.code}
                    </TableCell>
                    <TableCell className="font-medium text-neutral-900 dark:text-neutral-100">
                      {a.name}
                      {a.description && (
                        <p className="text-xs text-neutral-500">{a.description}</p>
                      )}
                    </TableCell>
                    <TableCell className="capitalize text-sm">
                      <Badge variant="info">{a.account_type}</Badge>
                    </TableCell>
                    <TableCell className="capitalize font-mono text-sm">
                      {a.normal_balance}
                    </TableCell>
                    <TableCell className="text-sm text-neutral-500">
                      {a.sub_type || '—'}
                    </TableCell>
                    <TableCell>
                      {a.is_system ? (
                        <Badge variant="warning">System</Badge>
                      ) : (
                        <span className="text-neutral-400 text-xs">Custom</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={a.is_active ? 'income' : 'neutral'}>
                        {a.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Tab 3: Trial Balance */}
      {activeTab === 'trial_balance' && (
        <div>
          {trialBalance && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-neutral-500 uppercase">
                    Balancing Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {trialBalance.is_balanced ? (
                    <div className="flex items-center gap-2 text-emerald-600 font-bold text-lg">
                      <span>✓ EQUATION BALANCED</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-rose-600 font-bold text-lg">
                      <span>✗ UNBALANCED</span>
                    </div>
                  )}
                  <p className="text-xs text-neutral-500 mt-1">Σ Debits == Σ Credits verified</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-neutral-500 uppercase">
                    Total Debits
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FinancialAmount
                    amount={Number(trialBalance.total_debits)}
                    currency="INR"
                    className="text-xl font-bold text-neutral-900 dark:text-neutral-100"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-neutral-500 uppercase">
                    Total Credits
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FinancialAmount
                    amount={Number(trialBalance.total_credits)}
                    currency="INR"
                    className="text-xl font-bold text-neutral-900 dark:text-neutral-100"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-neutral-500 uppercase">
                    Discrepancy / Difference
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FinancialAmount
                    amount={Number(trialBalance.difference)}
                    currency="INR"
                    className={`text-xl font-bold ${
                      Number(trialBalance.difference) === 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  />
                </CardContent>
              </Card>
            </div>
          )}

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account Code</TableHead>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead>Normal Balance</TableHead>
                  <TableHead className="text-right">Debit Balance (₹)</TableHead>
                  <TableHead className="text-right">Credit Balance (₹)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trialBalance?.entries?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-neutral-500">
                      No posted ledger activity recorded yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  trialBalance?.entries?.map((entry) => (
                    <TableRow key={entry.account_id}>
                      <TableCell className="font-mono font-bold text-neutral-900 dark:text-neutral-100">
                        {entry.code}
                      </TableCell>
                      <TableCell className="font-medium text-neutral-900 dark:text-neutral-100">
                        {entry.name}
                      </TableCell>
                      <TableCell className="capitalize text-sm">
                        <Badge variant="info">{entry.account_type}</Badge>
                      </TableCell>
                      <TableCell className="capitalize font-mono text-sm">
                        {entry.normal_balance}
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        {Number(entry.debit_balance) > 0 ? (
                          <FinancialAmount amount={Number(entry.debit_balance)} currency="INR" />
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        {Number(entry.credit_balance) > 0 ? (
                          <FinancialAmount amount={Number(entry.credit_balance)} currency="INR" />
                        ) : (
                          '—'
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
                {trialBalance && trialBalance.entries.length > 0 && (
                  <TableRow className="bg-neutral-100 dark:bg-neutral-900 font-bold border-t-2 border-neutral-300 dark:border-neutral-700">
                    <TableCell colSpan={4} className="text-right uppercase tracking-wider">
                      Grand Totals:
                    </TableCell>
                    <TableCell className="text-right font-mono text-base">
                      <FinancialAmount amount={Number(trialBalance.total_debits)} currency="INR" />
                    </TableCell>
                    <TableCell className="text-right font-mono text-base">
                      <FinancialAmount amount={Number(trialBalance.total_credits)} currency="INR" />
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Modal 1: Record Draft Journal Entry */}
      <Modal
        isOpen={isCreateJournalOpen}
        onClose={() => setIsCreateJournalOpen(false)}
        title="Record Double-Entry Journal Entry"
      >
        <form onSubmit={handleSaveDraftJournal} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="journal-date" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                Posting Date
              </label>
              <Input
                id="journal-date"
                type="date"
                value={journalDate}
                onChange={(e) => setJournalDate(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="journal-desc" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                Description / Memo
              </label>
              <Input
                id="journal-desc"
                placeholder="e.g. Monthly cloud hosting prepayment"
                value={journalDesc}
                onChange={(e) => setJournalDesc(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase text-neutral-500">Journal Lines</span>
              <Button type="button" variant="ghost" size="sm" onClick={handleAddLine}>
                + Add Line
              </Button>
            </div>

            <div className="space-y-3">
              {journalLines.map((line, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="flex-1">
                    <select
                      value={line.ledger_account_id}
                      onChange={(e) => handleLineChange(idx, 'ledger_account_id', e.target.value)}
                      required
                      className="w-full text-xs border border-neutral-300 dark:border-neutral-700 rounded px-2 py-1.5 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
                    >
                      <option value="">Select Ledger Account...</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} — {a.name} ({a.account_type.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="w-24">
                    <select
                      value={line.entry_type}
                      onChange={(e) => handleLineChange(idx, 'entry_type', e.target.value as 'debit' | 'credit')}
                      className="w-full text-xs border border-neutral-300 dark:border-neutral-700 rounded px-2 py-1.5 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 font-bold"
                    >
                      <option value="debit">DEBIT</option>
                      <option value="credit">CREDIT</option>
                    </select>
                  </div>
                  <div className="w-32">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Amount (₹)"
                      value={line.amount}
                      onChange={(e) => handleLineChange(idx, 'amount', e.target.value)}
                      required
                    />
                  </div>
                  {journalLines.length > 2 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveLine(idx)}
                      className="text-rose-600 hover:text-rose-700"
                    >
                      ✕
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Live Debit/Credit Balance Calculation */}
            <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-xs">
              <div>
                <span>Total Debits: </span>
                <span className="font-mono font-bold">₹{liveTotalDebits.toFixed(2)}</span>
                <span className="ml-4">Total Credits: </span>
                <span className="font-mono font-bold">₹{liveTotalCredits.toFixed(2)}</span>
              </div>
              <div>
                {isLiveDraftBalanced ? (
                  <Badge variant="income">BALANCED (Difference: ₹0.00)</Badge>
                ) : (
                  <Badge variant="expense">
                    UNBALANCED (Diff: ₹{Math.abs(liveTotalDebits - liveTotalCredits).toFixed(2)})
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateJournalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isLoading}>
              Save Draft Journal
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal 2: Inspect Journal Lines */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={selectedJournal ? `Journal Entry: ${selectedJournal.entry_number}` : 'Journal Details'}
      >
        {selectedJournal && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-neutral-500">Date:</span>
                <p className="font-semibold">{selectedJournal.entry_date}</p>
              </div>
              <div>
                <span className="text-neutral-500">Status:</span>
                <p>
                  <Badge
                    variant={
                      selectedJournal.status === 'posted'
                        ? 'income'
                        : selectedJournal.status === 'draft'
                        ? 'warning'
                        : 'neutral'
                    }
                  >
                    {selectedJournal.status.toUpperCase()}
                  </Badge>
                </p>
              </div>
              <div className="col-span-2">
                <span className="text-neutral-500">Description:</span>
                <p className="font-medium text-neutral-900 dark:text-neutral-100">{selectedJournal.description}</p>
              </div>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Line</TableHead>
                  <TableHead>Ledger Account</TableHead>
                  <TableHead className="text-right">Debit (₹)</TableHead>
                  <TableHead className="text-right">Credit (₹)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {selectedJournal.lines.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell className="font-mono text-xs">{l.line_number}</TableCell>
                    <TableCell>
                      <span className="font-mono font-bold text-xs">{l.ledger_account_code}</span>
                      <p className="text-xs text-neutral-600 dark:text-neutral-400">{l.ledger_account_name}</p>
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">
                      {l.entry_type === 'debit' ? (
                        <FinancialAmount amount={Number(l.amount)} currency="INR" />
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">
                      {l.entry_type === 'credit' ? (
                        <FinancialAmount amount={Number(l.amount)} currency="INR" />
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-bold border-t border-neutral-300 dark:border-neutral-700">
                  <TableCell colSpan={2} className="text-right">
                    Totals:
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    <FinancialAmount amount={Number(selectedJournal.total_debits)} currency="INR" />
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    <FinancialAmount amount={Number(selectedJournal.total_credits)} currency="INR" />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setIsDetailModalOpen(false)}>
                Close
              </Button>
              {selectedJournal.status === 'draft' && (
                <Button
                  variant="primary"
                  onClick={async () => {
                    await handlePostJournal(selectedJournal.id);
                    setIsDetailModalOpen(false);
                  }}
                >
                  Post to Authoritative Ledger
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Modal 3: Compensating Reversal */}
      <Modal
        isOpen={isReverseModalOpen}
        onClose={() => setIsReverseModalOpen(false)}
        title="Execute Compensating Reversal"
      >
        <form onSubmit={handleConfirmReverse} className="space-y-4">
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Posted journal entries cannot be deleted. This operation will generate an inverted
            reversal entry, restore prior ledger balances, and mark the original entry as reversed.
          </p>
          <div>
            <label htmlFor="reversal-reason" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
              Reversal Reason (Mandatory Audit Justification)
            </label>
            <Input
              id="reversal-reason"
              placeholder="e.g. Erroneous invoice double entry verified by auditor"
              value={reversalReason}
              onChange={(e) => setReversalReason(e.target.value)}
              required
            />
          </div>
          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsReverseModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={isLoading || !reversalReason}>
              Confirm Reversal
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal 4: Create Ledger Account */}
      <Modal
        isOpen={isCreateAccountOpen}
        onClose={() => setIsCreateAccountOpen(false)}
        title="Create Chart of Accounts Ledger Account"
      >
        <form onSubmit={handleCreateAccount} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="new-acct-code" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                Account Code
              </label>
              <Input
                id="new-acct-code"
                placeholder="e.g. 5085"
                value={newAccountCode}
                onChange={(e) => setNewAccountCode(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="new-acct-type" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                Classification
              </label>
              <select
                id="new-acct-type"
                value={newAccountType}
                onChange={(e) => setNewAccountType(e.target.value)}
                className="w-full text-sm border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
              >
                <option value="asset">Asset (Debit Normal)</option>
                <option value="liability">Liability (Credit Normal)</option>
                <option value="equity">Equity (Credit Normal)</option>
                <option value="revenue">Revenue (Credit Normal)</option>
                <option value="expense">Expense (Debit Normal)</option>
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="new-acct-name" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
              Account Name
            </label>
            <Input
              id="new-acct-name"
              placeholder="e.g. Legal & Professional Charges"
              value={newAccountName}
              onChange={(e) => setNewAccountName(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="new-acct-desc" className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
              Description (Optional)
            </label>
            <Input
              id="new-acct-desc"
              placeholder="e.g. Retainer fees for legal compliance"
              value={newAccountDesc}
              onChange={(e) => setNewAccountDesc(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateAccountOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isLoading}>
              Create Account
            </Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  );
};
