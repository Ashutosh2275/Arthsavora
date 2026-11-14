import React, { useEffect, useState } from 'react';
import {
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Sliders,
  History,
  FileSpreadsheet,
  ArrowRight,
  ShieldCheck,
  Eye,
  Edit2,
  Trash2,
} from 'lucide-react';
import { useImportStore } from '../store/useImportStore';
import { useAccountStore } from '../store/useAccountStore';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { FinancialAmount } from '../components/ui/financial-amount';
import { Modal } from '../components/ui/modal';
import { Alert } from '../components/ui/alert';
import { ImportCandidateResponse } from '@arthsavora/contracts';

export const Import: React.FC = () => {
  const {
    jobs,
    candidates,
    lastUploadResult,
    reconciliation,
    isLoading,
    isUploading,
    isConfirming,
    error,
    fetchJobs,
    uploadFile,
    confirmImport,
    cancelJob,
    toggleCandidateSelection,
    toggleSelectAll,
    updateCandidate,
    fetchReconciliation,
    clearError,
    resetCurrentUpload,
  } = useImportStore();

  const { accounts, fetchAccounts } = useAccountStore();

  const [activeTab, setActiveTab] = useState<'upload' | 'history'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [showAdvancedMapping, setShowAdvancedMapping] = useState<boolean>(false);
  const [columnMapping, setColumnMapping] = useState({
    date: '',
    description: '',
    debit: '',
    credit: '',
    amount: '',
    ref_no: '',
    balance: '',
  });

  const [statusFilter, setStatusFilter] = useState<'all' | 'valid' | 'duplicate' | 'invalid'>('all');
  const [editingCandidate, setEditingCandidate] = useState<ImportCandidateResponse | null>(null);
  const [editForm, setEditForm] = useState({
    description: '',
    transaction_date: '',
    amount: '',
    direction: 'outflow',
  });

  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchAccounts();
    fetchJobs();
  }, [fetchAccounts, fetchJobs]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      const activeMapping = Object.fromEntries(
        Object.entries(columnMapping).filter(([_, v]) => v.trim() !== '')
      );

      const res = await uploadFile(
        selectedFile,
        undefined,
        selectedAccountId || undefined,
        Object.keys(activeMapping).length > 0 ? activeMapping : undefined,
      );

      if (res.batch_id) {
        await fetchReconciliation(res.batch_id);
      }
    } catch {
      // Error handled in store
    }
  };

  const handleConfirmSubmit = async () => {
    if (!lastUploadResult) return;
    try {
      const res = await confirmImport(
        lastUploadResult.job_id,
        lastUploadResult.batch_id,
        selectedAccountId || undefined,
      );
      setConfirmModalOpen(false);
      setSuccessMessage(`Successfully imported and posted ${res.imported_count} transactions to the General Ledger!`);
      resetCurrentUpload();
      fetchJobs();
    } catch {
      // Error in store
    }
  };

  const handleSaveCandidateEdit = async () => {
    if (!editingCandidate) return;
    try {
      await updateCandidate(editingCandidate.id, {
        description: editForm.description,
        transaction_date: editForm.transaction_date,
        amount: editForm.amount ? Number(editForm.amount) : undefined,
        direction: editForm.direction,
      });
      setEditingCandidate(null);
    } catch {
      // Error in store
    }
  };

  const filteredCandidates = candidates.filter((c) => {
    if (statusFilter === 'valid') return c.validation_status === 'valid' && c.duplicate_status === 'none';
    if (statusFilter === 'duplicate') return c.duplicate_status !== 'none';
    if (statusFilter === 'invalid') return c.validation_status !== 'valid';
    return true;
  });

  const selectedCount = candidates.filter((c) => c.selected_for_import && c.validation_status === 'valid').length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Upload className="w-6 h-6 text-brand-600" />
            Financial Data Acquisition & Statement Import
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Import statements from Indian banks (HDFC, SBI, ICICI, Axis, Kotak), Credit Cards, and generic CSV/XLSX/PDF files with audit-grade validation and double-entry General Ledger posting.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === 'upload' ? 'primary' : 'outline'}
            onClick={() => setActiveTab('upload')}
            className="flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            New Import
          </Button>
          <Button
            variant={activeTab === 'history' ? 'primary' : 'outline'}
            onClick={() => {
              setActiveTab('history');
              fetchJobs();
            }}
            className="flex items-center gap-2"
          >
            <History className="w-4 h-4" />
            Import History
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="error" onDismiss={clearError}>
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert variant="info" onDismiss={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}

      {/* Main Tab Views */}
      {activeTab === 'upload' && (
        <div className="space-y-6">
          {/* Step 1: Upload Card (If no active upload in review) */}
          {!lastUploadResult && (
            <div className="p-6 bg-card border border-border rounded-xl shadow-sm space-y-6">
              <div className="flex items-center gap-2 border-b border-border pb-4">
                <FileSpreadsheet className="w-5 h-5 text-brand-600" />
                <h2 className="text-lg font-semibold text-foreground">Upload Financial Statement</h2>
              </div>

              <form onSubmit={handleUpload} className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Target Financial Account
                    </label>
                    <select
                      className="w-full h-10 px-3 py-2 bg-background border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500"
                      value={selectedAccountId}
                      onChange={(e) => setSelectedAccountId(e.target.value)}
                    >
                      <option value="">Auto-Detect / Select Destination Account...</option>
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.name} ({acc.account_type.toUpperCase()} - {acc.currency})
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-muted-foreground mt-1">
                      Account balances and general ledger journal entries will post against this destination account.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Statement File (CSV, XLSX, or PDF)
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="file"
                        accept=".csv,.xlsx,.pdf"
                        onChange={handleFileChange}
                        className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Max file size: 10 MB. Magic signature and cryptographic SHA-256 verification applied.
                    </p>
                  </div>
                </div>

                {/* Collapsible Column Mapping Accordion */}
                <div className="border border-border rounded-lg p-4 bg-muted/20">
                  <button
                    type="button"
                    onClick={() => setShowAdvancedMapping(!showAdvancedMapping)}
                    className="flex items-center justify-between w-full text-sm font-medium text-foreground"
                  >
                    <span className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-brand-600" />
                      Custom Column Header Mapping (Optional for custom CSV/XLSX)
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {showAdvancedMapping ? 'Hide' : 'Configure Custom Headers'}
                    </span>
                  </button>

                  {showAdvancedMapping && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-3 border-t border-border">
                      <div>
                        <label className="block text-xs text-muted-foreground mb-1">Date Header</label>
                        <input
                          type="text"
                          placeholder="e.g. Txn Date"
                          className="w-full h-8 px-2 text-xs bg-background border border-border rounded"
                          value={columnMapping.date}
                          onChange={(e) => setColumnMapping({ ...columnMapping, date: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-muted-foreground mb-1">Description Header</label>
                        <input
                          type="text"
                          placeholder="e.g. Narration"
                          className="w-full h-8 px-2 text-xs bg-background border border-border rounded"
                          value={columnMapping.description}
                          onChange={(e) => setColumnMapping({ ...columnMapping, description: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-muted-foreground mb-1">Debit / Withdrawal</label>
                        <input
                          type="text"
                          placeholder="e.g. Withdrawal Amt."
                          className="w-full h-8 px-2 text-xs bg-background border border-border rounded"
                          value={columnMapping.debit}
                          onChange={(e) => setColumnMapping({ ...columnMapping, debit: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-muted-foreground mb-1">Credit / Deposit</label>
                        <input
                          type="text"
                          placeholder="e.g. Deposit Amt."
                          className="w-full h-8 px-2 text-xs bg-background border border-border rounded"
                          value={columnMapping.credit}
                          onChange={(e) => setColumnMapping({ ...columnMapping, credit: e.target.value })}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={!selectedFile || isUploading}
                    className="flex items-center gap-2"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Extracting & Normalizing...
                      </>
                    ) : (
                      <>
                        <ArrowRight className="w-4 h-4" />
                        Inspect & Review Statement
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* Step 2: Candidate Review Table (When an upload has succeeded) */}
          {lastUploadResult && (
            <div className="space-y-6">
              {/* Summary Metrics & Reconciliation Card */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 bg-card border border-border rounded-xl">
                  <p className="text-xs text-muted-foreground uppercase font-medium">Total Extracted</p>
                  <p className="text-2xl font-bold text-foreground mt-1">{lastUploadResult.total_records}</p>
                  <p className="text-xs text-muted-foreground mt-1">Source: {lastUploadResult.original_filename}</p>
                </div>
                <div className="p-4 bg-card border border-border rounded-xl">
                  <p className="text-xs text-muted-foreground uppercase font-medium">Valid Ready to Post</p>
                  <p className="text-2xl font-bold text-success-600 mt-1">{lastUploadResult.valid_records}</p>
                  <Badge variant="income" className="mt-1">Passed Validation</Badge>
                </div>
                <div className="p-4 bg-card border border-border rounded-xl">
                  <p className="text-xs text-muted-foreground uppercase font-medium">Suspected Duplicates</p>
                  <p className="text-2xl font-bold text-warning-600 mt-1">{lastUploadResult.duplicate_records}</p>
                  <Badge variant="warning" className="mt-1">Flagged for Review</Badge>
                </div>
                <div className="p-4 bg-card border border-border rounded-xl">
                  <p className="text-xs text-muted-foreground uppercase font-medium">Invalid / Ambiguous</p>
                  <p className="text-2xl font-bold text-destructive-600 mt-1">{lastUploadResult.invalid_records}</p>
                  <Badge variant="expense" className="mt-1">Requires Correction</Badge>
                </div>
              </div>

              {/* Statement Balance Reconciliation Card */}
              {reconciliation && reconciliation.opening_balance && (
                <div className="p-4 bg-muted/30 border border-border rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-brand-600" />
                      Statement Balance Reconciliation
                    </span>
                    {reconciliation.is_reconciled ? (
                      <Badge variant="income" className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Reconciled (Zero Variance)
                      </Badge>
                    ) : (
                      <Badge variant="warning" className="flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> Discrepancy Detected
                      </Badge>
                    )}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                    <div>
                      <p className="text-muted-foreground">Opening Balance</p>
                      <p className="font-semibold text-foreground mt-0.5">₹{reconciliation.opening_balance}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Total Inflows (+)</p>
                      <p className="font-semibold text-success-600 mt-0.5">₹{reconciliation.total_inflows}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Total Outflows (-)</p>
                      <p className="font-semibold text-destructive-600 mt-0.5">₹{reconciliation.total_outflows}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Calculated Closing</p>
                      <p className="font-semibold text-foreground mt-0.5">₹{reconciliation.calculated_closing_balance || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Reported Closing</p>
                      <p className="font-semibold text-foreground mt-0.5">₹{reconciliation.closing_balance || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Review Filter Bar */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-card border border-border rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase text-muted-foreground mr-2">Filter Rows:</span>
                  <button
                    onClick={() => setStatusFilter('all')}
                    className={`px-3 py-1 text-xs rounded-full border ${
                      statusFilter === 'all' ? 'bg-brand-50 border-brand-500 text-brand-700 font-semibold' : 'border-border text-muted-foreground'
                    }`}
                  >
                    All ({candidates.length})
                  </button>
                  <button
                    onClick={() => setStatusFilter('valid')}
                    className={`px-3 py-1 text-xs rounded-full border ${
                      statusFilter === 'valid' ? 'bg-emerald-50 border-emerald-500 text-emerald-700 font-semibold' : 'border-border text-muted-foreground'
                    }`}
                  >
                    Valid Only
                  </button>
                  <button
                    onClick={() => setStatusFilter('duplicate')}
                    className={`px-3 py-1 text-xs rounded-full border ${
                      statusFilter === 'duplicate' ? 'bg-amber-50 border-amber-500 text-amber-700 font-semibold' : 'border-border text-muted-foreground'
                    }`}
                  >
                    Duplicates Only
                  </button>
                  <button
                    onClick={() => setStatusFilter('invalid')}
                    className={`px-3 py-1 text-xs rounded-full border ${
                      statusFilter === 'invalid' ? 'bg-rose-50 border-rose-500 text-rose-700 font-semibold' : 'border-border text-muted-foreground'
                    }`}
                  >
                    Invalid Only
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleSelectAll(true)}
                  >
                    Select All Valid
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleSelectAll(false)}
                  >
                    Deselect All
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => cancelJob(lastUploadResult.job_id)}
                  >
                    Cancel Import
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={selectedCount === 0 || isConfirming}
                    onClick={() => setConfirmModalOpen(true)}
                    className="flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Confirm Import ({selectedCount} Rows)
                  </Button>
                </div>
              </div>

              {/* Candidate Table */}
              <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs uppercase font-medium">
                      <tr>
                        <th className="py-3 px-4 w-10 text-center">Import</th>
                        <th className="py-3 px-4 w-12">#</th>
                        <th className="py-3 px-4">Date</th>
                        <th className="py-3 px-4">Description / Narration</th>
                        <th className="py-3 px-4">Ref / UTR</th>
                        <th className="py-3 px-4 text-right">Amount</th>
                        <th className="py-3 px-4">Direction</th>
                        <th className="py-3 px-4 text-center">Validation</th>
                        <th className="py-3 px-4 text-center">Duplicates</th>
                        <th className="py-3 px-4 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {filteredCandidates.length === 0 ? (
                        <tr>
                          <td colSpan={10} className="py-8 text-center text-muted-foreground">
                            No candidates match the selected filter.
                          </td>
                        </tr>
                      ) : (
                        filteredCandidates.map((c) => (
                          <tr
                            key={c.id}
                            className={`hover:bg-muted/30 transition-colors ${
                              !c.selected_for_import ? 'opacity-60 bg-muted/10' : ''
                            }`}
                          >
                            <td className="py-3 px-4 text-center">
                              <input
                                type="checkbox"
                                checked={c.selected_for_import}
                                disabled={c.validation_status !== 'valid'}
                                onChange={(e) => toggleCandidateSelection(c.id, e.target.checked)}
                                className="rounded border-border text-brand-600 focus:ring-brand-500"
                              />
                            </td>
                            <td className="py-3 px-4 text-xs text-muted-foreground">{c.source_row_number}</td>
                            <td className="py-3 px-4 font-mono text-xs">
                              {c.normalized_data.transaction_date || (
                                <span className="text-destructive-600 italic">Missing Date</span>
                              )}
                            </td>
                            <td className="py-3 px-4 font-medium max-w-xs truncate" title={c.normalized_data.description || ''}>
                              {c.normalized_data.description || <span className="text-destructive-600 italic">Empty</span>}
                            </td>
                            <td className="py-3 px-4 font-mono text-xs text-muted-foreground">
                              {c.normalized_data.reference_number || '-'}
                            </td>
                            <td className="py-3 px-4 text-right font-medium">
                              {c.normalized_data.amount ? (
                                <FinancialAmount
                                  amount={Number(c.normalized_data.amount)}
                                  currency="INR"
                                  type={c.normalized_data.direction === 'inflow' ? 'income' : 'expense'}
                                />
                              ) : (
                                <span className="text-destructive-600 italic text-xs">Invalid</span>
                              )}
                            </td>
                            <td className="py-3 px-4">
                              <Badge
                                variant={c.normalized_data.direction === 'inflow' ? 'income' : 'expense'}
                                size="sm"
                              >
                                {c.normalized_data.direction}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-center">
                              {c.validation_status === 'valid' ? (
                                <Badge variant="income" size="sm">Valid</Badge>
                              ) : (
                                <Badge
                                  variant="expense"
                                  size="sm"
                                  title={c.validation_errors.join('; ')}
                                >
                                  {c.validation_status}
                                </Badge>
                              )}
                            </td>
                            <td className="py-3 px-4 text-center">
                              {c.duplicate_status === 'none' ? (
                                <Badge variant="neutral" size="sm">Clean</Badge>
                              ) : (
                                <Badge
                                  variant="warning"
                                  size="sm"
                                  title={c.duplicate_reason || 'Suspected Duplicate'}
                                >
                                  {c.duplicate_status}
                                </Badge>
                              )}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingCandidate(c);
                                  setEditForm({
                                    description: c.normalized_data.description || '',
                                    transaction_date: c.normalized_data.transaction_date || '',
                                    amount: c.normalized_data.amount || '',
                                    direction: c.normalized_data.direction || 'outflow',
                                  });
                                }}
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </Button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Statement Import History</h2>
            <Button variant="ghost" size="sm" onClick={() => fetchJobs()} className="flex items-center gap-1">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs uppercase font-medium">
                <tr>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Uploaded At</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-center">Processed</th>
                  <th className="py-3 px-4 text-center">Imported</th>
                  <th className="py-3 px-4 text-center">Duplicates</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      No statement imports recorded yet.
                    </td>
                  </tr>
                ) : (
                  jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-muted/30">
                      <td className="py-3 px-4 font-medium flex items-center gap-2">
                        <FileText className="w-4 h-4 text-brand-600" />
                        {j.original_filename || 'Unknown Statement'}
                      </td>
                      <td className="py-3 px-4 uppercase text-xs font-mono">{j.source_type}</td>
                      <td className="py-3 px-4 text-xs text-muted-foreground">
                        {new Date(j.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          variant={
                            j.status === 'completed'
                              ? 'income'
                              : j.status === 'awaiting_review'
                              ? 'warning'
                              : j.status === 'failed'
                              ? 'expense'
                              : 'neutral'
                          }
                          size="sm"
                        >
                          {j.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-center font-mono">{j.total_records}</td>
                      <td className="py-3 px-4 text-center font-mono text-emerald-600 font-semibold">{j.imported_records}</td>
                      <td className="py-3 px-4 text-center font-mono text-amber-600">{j.duplicate_records}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        title="Confirm Statement Ingestion"
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            You are about to finalize <span className="font-semibold text-foreground">{selectedCount}</span> validated transactions.
            Each transaction will be recorded in the operational register and posted to the double-entry General Ledger.
          </p>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1">
              Select Destination Financial Account
            </label>
            <select
              className="w-full h-10 px-3 py-2 bg-background border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
            >
              <option value="">Select Account...</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.account_type.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div className="p-3 bg-muted/40 border border-border rounded-lg text-xs space-y-1">
            <p className="font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Double-Entry General Ledger Guarantee:
            </p>
            <p className="text-muted-foreground">
              - Balance sheet accounts are updated with exact minor unit (paise) precision.
              - Inflow records credit revenue or asset transfers. Outflow records debit operational expenses.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button variant="ghost" onClick={() => setConfirmModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!selectedAccountId || isConfirming}
              onClick={handleConfirmSubmit}
            >
              {isConfirming ? 'Posting to Ledger...' : `Confirm & Post ${selectedCount} Items`}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Candidate Edit Modal */}
      <Modal
        isOpen={editingCandidate !== null}
        onClose={() => setEditingCandidate(null)}
        title="Edit Transaction Candidate"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Date</label>
            <input
              type="date"
              className="w-full h-9 px-3 text-sm bg-background border border-border rounded-md"
              value={editForm.transaction_date}
              onChange={(e) => setEditForm({ ...editForm, transaction_date: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Description / Narration</label>
            <input
              type="text"
              className="w-full h-9 px-3 text-sm bg-background border border-border rounded-md"
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Amount</label>
              <input
                type="number"
                step="0.01"
                className="w-full h-9 px-3 text-sm bg-background border border-border rounded-md"
                value={editForm.amount}
                onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Direction</label>
              <select
                className="w-full h-9 px-3 text-sm bg-background border border-border rounded-md"
                value={editForm.direction}
                onChange={(e) => setEditForm({ ...editForm, direction: e.target.value })}
              >
                <option value="outflow">Outflow (Debit)</option>
                <option value="inflow">Inflow (Credit)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button variant="ghost" onClick={() => setEditingCandidate(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSaveCandidateEdit}>
              Save Changes
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
