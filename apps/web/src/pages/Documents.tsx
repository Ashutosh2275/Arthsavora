import React, { useEffect, useRef, useState } from 'react';
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  RefreshCw,
  Search,
  Check,
  ShieldCheck,
  FileCheck,
  Building,
  Calendar,
  CreditCard,
  Tag,
  Hash,
  Clock,
  Trash2,
  ExternalLink,
  ChevronRight,
  Filter,
} from 'lucide-react';
import type { FinancialDocument, TransactionMatchCandidate } from '@arthsavora/contracts';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useDocumentStore } from '@/store/useDocumentStore';
import { useAccountStore } from '@/store/useAccountStore';

export function Documents() {
  const {
    documents,
    selectedDocument,
    matches,
    isLoading,
    isUploading,
    isProcessing,
    isMatching,
    error,
    fetchDocuments,
    fetchDocumentDetails,
    uploadDocument,
    processDocument,
    correctExtraction,
    confirmTransaction,
    findMatches,
    associateTransaction,
    rejectDocument,
    deleteDocument,
    setSelectedDocument,
    clearError,
  } = useDocumentStore();

  const { accounts, fetchAccounts } = useAccountStore();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Editable form state for current document
  const [editMerchant, setEditMerchant] = useState('');
  const [editDate, setEditDate] = useState('');
  const [editTotal, setEditTotal] = useState('');
  const [editSubtotal, setEditSubtotal] = useState('');
  const [editCgst, setEditCgst] = useState('');
  const [editSgst, setEditSgst] = useState('');
  const [editIgst, setEditIgst] = useState('');
  const [editGstin, setEditGstin] = useState('');
  const [editPaymentMethod, setEditPaymentMethod] = useState('');
  const [editPaymentRef, setEditPaymentRef] = useState('');
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments(undefined, {
      status: statusFilter === 'all' ? undefined : statusFilter,
      search: searchQuery || undefined,
    });
    fetchAccounts();
  }, [fetchDocuments, fetchAccounts, statusFilter, searchQuery]);

  useEffect(() => {
    if (accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts, selectedAccountId]);

  // Sync edit form when selectedDocument changes
  useEffect(() => {
    if (selectedDocument && selectedDocument.extractions && selectedDocument.extractions.length > 0) {
      const ext = selectedDocument.extractions[0];
      const data = ext.structured_data || {};
      setEditMerchant(data.merchant_name || '');
      setEditDate(data.receipt_date || '');
      setEditTotal(data.total_amount || '');
      setEditSubtotal(data.subtotal || '');
      setEditCgst(data.taxes?.cgst || '');
      setEditSgst(data.taxes?.sgst || '');
      setEditIgst(data.taxes?.igst || '');
      setEditGstin(data.gstin || '');
      setEditPaymentMethod(data.payment_method || 'unknown');
      setEditPaymentRef(data.payment_reference || '');

      findMatches(selectedDocument.id);
    } else {
      setEditMerchant('');
      setEditDate('');
      setEditTotal('');
      setEditSubtotal('');
      setEditCgst('');
      setEditSgst('');
      setEditIgst('');
      setEditGstin('');
      setEditPaymentMethod('unknown');
      setEditPaymentRef('');
    }
  }, [selectedDocument, findMatches]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    try {
      setActionSuccess(null);
      const doc = await uploadDocument(file, undefined, 'receipt', true);
      setSelectedDocument(doc);
      setActionSuccess(`Successfully uploaded and scanned ${file.name}`);
    } catch {
      // Error is tracked in store
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleSaveCorrections = async () => {
    if (!selectedDocument) return;
    try {
      setActionSuccess(null);
      await correctExtraction(selectedDocument.id, {
        merchant_name: editMerchant,
        receipt_date: editDate,
        total_amount: editTotal,
        subtotal: editSubtotal,
        gstin: editGstin,
        payment_method: editPaymentMethod,
        payment_reference: editPaymentRef,
        taxes: {
          cgst: editCgst,
          sgst: editSgst,
          igst: editIgst,
          gstin: editGstin,
        },
      });
      setActionSuccess('Field corrections saved successfully.');
    } catch {
      // Handled in store
    }
  };

  const handleConfirmAndPost = async () => {
    if (!selectedDocument || !selectedAccountId) return;
    try {
      setActionSuccess(null);
      await confirmTransaction(selectedDocument.id, selectedAccountId, {
        merchant_name: editMerchant,
        receipt_date: editDate,
        total_amount: editTotal,
        subtotal: editSubtotal,
        gstin: editGstin,
        payment_method: editPaymentMethod,
        payment_reference: editPaymentRef,
      });
      setActionSuccess('Receipt confirmed and authoritative transaction posted to ledger!');
    } catch {
      // Handled in store
    }
  };

  const handleAssociateMatch = async (match: TransactionMatchCandidate) => {
    if (!selectedDocument) return;
    try {
      setActionSuccess(null);
      await associateTransaction(
        selectedDocument.id,
        match.transaction_id,
        Number(match.match_score),
        'Linked via match candidate scan'
      );
      setActionSuccess('Receipt successfully linked to existing transaction!');
    } catch {
      // Handled in store
    }
  };

  const handleReject = async () => {
    if (!selectedDocument) return;
    try {
      setActionSuccess(null);
      await rejectDocument(selectedDocument.id, 'User marked as rejected');
      setActionSuccess('Document marked as rejected.');
    } catch {
      // Handled in store
    }
  };

  const getStatusBadgeVariant = (st: string) => {
    switch (st) {
      case 'confirmed':
        return 'income';
      case 'extracted':
        return 'info';
      case 'review_required':
        return 'warning';
      case 'rejected':
      case 'failed':
        return 'expense';
      default:
        return 'neutral';
    }
  };

  const latestExtraction =
    selectedDocument?.extractions && selectedDocument.extractions.length > 0
      ? selectedDocument.extractions[0]
      : null;

  const isConfirmed = selectedDocument?.status === 'confirmed';
  const isRejected = selectedDocument?.status === 'rejected';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileText className="h-7 w-7 text-indigo-400" />
            Receipt Intelligence & Documents
          </h1>
          <p className="text-sm text-slate-400">
            India-first receipt OCR, GSTIN validation, intelligent entity extraction, and side-by-side review.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            {isUploading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Upload Document
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {actionSuccess && (
        <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
            <span className="text-sm">{actionSuccess}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setActionSuccess(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Upload Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
          isDragOver
            ? 'border-indigo-500 bg-indigo-500/10'
            : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900'
        }`}
      >
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="h-12 w-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400">
            <Upload className="h-6 w-6" />
          </div>
          <p className="text-sm font-medium text-slate-200">
            Drop physical receipt scans, JPEG, PNG, WebP images, or PDF invoices
          </p>
          <p className="text-xs text-slate-500">
            Up to 15MB. Indian GSTIN, CGST/SGST/IGST, line items, and payment references parsed automatically.
          </p>
        </div>
      </div>

      {/* Main 2-Column Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Documents List (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="p-4 bg-slate-900/80 border-slate-800 space-y-3">
            {/* Filter & Search Bar */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <Input
                  placeholder="Search receipts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9 text-xs bg-slate-950 border-slate-800"
                />
              </div>
              <select
                aria-label="Filter documents by status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-9 px-2.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-300"
              >
                <option value="all">All</option>
                <option value="review_required">Review Required</option>
                <option value="extracted">Extracted</option>
                <option value="confirmed">Confirmed</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            {/* List */}
            <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
              {isLoading && documents.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-500">Loading documents...</div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-500">No documents found.</div>
              ) : (
                documents.map((doc) => {
                  const isSelected = selectedDocument?.id === doc.id;
                  const ext = doc.extractions && doc.extractions.length > 0 ? doc.extractions[0] : null;
                  const data = (ext?.structured_data || {}) as Record<string, any>;
                  return (
                    <div
                      key={doc.id}
                      onClick={() => fetchDocumentDetails(doc.id)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                        isSelected
                          ? 'border-indigo-500/60 bg-indigo-500/10'
                          : 'border-slate-800/80 bg-slate-950/60 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-semibold text-slate-200 truncate max-w-[170px]">
                          {data.merchant_name || doc.original_filename}
                        </span>
                        <Badge variant={getStatusBadgeVariant(doc.status)} size="sm">
                          {doc.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>{data.receipt_date || doc.created_at.slice(0, 10)}</span>
                        <span className="font-mono font-medium text-slate-200">
                          {data.total_amount ? `₹${data.total_amount}` : '-'}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Review & Detail Panel (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {selectedDocument ? (
            <div className="space-y-4">
              {/* Document Overview Bar */}
              <Card className="p-4 bg-slate-900 border-slate-800 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{selectedDocument.original_filename}</h3>
                    <p className="text-xs text-slate-400">
                      {(selectedDocument.file_size / 1024).toFixed(1)} KB • {selectedDocument.mime_type} •{' '}
                      {selectedDocument.created_at.slice(0, 10)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={getStatusBadgeVariant(selectedDocument.status)}>
                    {selectedDocument.status.replace('_', ' ')}
                  </Badge>

                  {latestExtraction && (
                    <Badge
                      variant={
                        Number(latestExtraction.overall_confidence) >= 0.8
                          ? 'income'
                          : Number(latestExtraction.overall_confidence) >= 0.6
                          ? 'warning'
                          : 'expense'
                      }
                    >
                      {Math.round(Number(latestExtraction.overall_confidence) * 100)}% Confidence
                    </Badge>
                  )}

                  <a
                    href={`/api/v1/documents/${selectedDocument.id}/download?preview=true`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                  >
                    <Eye className="h-3.5 w-3.5" /> Preview File
                  </a>
                </div>
              </Card>

              {/* Extraction Validation Warnings Banner */}
              {latestExtraction && latestExtraction.validation_warnings.length > 0 && (
                <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4" /> Mathematical or Formatting Discrepancies
                  </div>
                  <ul className="list-disc pl-5 space-y-0.5">
                    {latestExtraction.validation_warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Verified Entities Form Card */}
              <Card className="p-5 bg-slate-900 border-slate-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <FileCheck className="h-4 w-4 text-indigo-400" />
                    Structured Financial Entities (Editable)
                  </h4>
                  <span className="text-xs text-slate-500">
                    Engine: {latestExtraction?.ocr_provider || 'Pending'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Merchant Name */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                      <Building className="h-3.5 w-3.5" /> Merchant / Counterparty
                    </label>
                    <Input
                      value={editMerchant}
                      onChange={(e) => setEditMerchant(e.target.value)}
                      disabled={isConfirmed}
                      className="bg-slate-950 border-slate-800 text-sm"
                    />
                  </div>

                  {/* Transaction Date */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" /> Transaction Date
                    </label>
                    <Input
                      type="date"
                      value={editDate}
                      onChange={(e) => setEditDate(e.target.value)}
                      disabled={isConfirmed}
                      className="bg-slate-950 border-slate-800 text-sm"
                    />
                  </div>

                  {/* Total Amount */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400">
                      Total Amount Payable (₹)
                    </label>
                    <Input
                      value={editTotal}
                      onChange={(e) => setEditTotal(e.target.value)}
                      disabled={isConfirmed}
                      className="bg-slate-950 border-slate-800 font-mono text-sm font-bold text-white"
                    />
                  </div>

                  {/* Subtotal */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400">
                      Subtotal / Taxable Value (₹)
                    </label>
                    <Input
                      value={editSubtotal}
                      onChange={(e) => setEditSubtotal(e.target.value)}
                      disabled={isConfirmed}
                      className="bg-slate-950 border-slate-800 font-mono text-sm"
                    />
                  </div>

                  {/* GSTIN */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Hash className="h-3.5 w-3.5" /> Indian GSTIN
                      </span>
                      {editGstin && (
                        <Badge variant="income" size="sm">
                          15-char GSTIN
                        </Badge>
                      )}
                    </label>
                    <Input
                      value={editGstin}
                      onChange={(e) => setEditGstin(e.target.value.toUpperCase())}
                      disabled={isConfirmed}
                      placeholder="e.g. 29AABCB2212M1Z2"
                      className="bg-slate-950 border-slate-800 font-mono text-xs uppercase"
                    />
                  </div>

                  {/* Payment Mode */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                      <CreditCard className="h-3.5 w-3.5" /> Payment Method & Reference
                    </label>
                    <div className="flex gap-2">
                      <select
                        aria-label="Payment method"
                        value={editPaymentMethod}
                        onChange={(e) => setEditPaymentMethod(e.target.value)}
                        disabled={isConfirmed}
                        className="h-10 px-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 capitalize"
                      >
                        <option value="upi">UPI</option>
                        <option value="card">Card</option>
                        <option value="cash">Cash</option>
                        <option value="netbanking">Netbanking</option>
                        <option value="unknown">Unknown</option>
                      </select>
                      <Input
                        value={editPaymentRef}
                        onChange={(e) => setEditPaymentRef(e.target.value)}
                        disabled={isConfirmed}
                        placeholder="UPI UTR / Ref"
                        className="bg-slate-950 border-slate-800 text-xs font-mono flex-1"
                      />
                    </div>
                  </div>
                </div>

                {/* Tax Breakdown Grid */}
                <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950 space-y-2">
                  <span className="text-xs font-semibold text-slate-300">GST Breakdown (₹)</span>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <span className="text-[11px] text-slate-500">CGST</span>
                      <Input
                        value={editCgst}
                        onChange={(e) => setEditCgst(e.target.value)}
                        disabled={isConfirmed}
                        className="h-8 text-xs font-mono bg-slate-900 border-slate-800"
                      />
                    </div>
                    <div>
                      <span className="text-[11px] text-slate-500">SGST</span>
                      <Input
                        value={editSgst}
                        onChange={(e) => setEditSgst(e.target.value)}
                        disabled={isConfirmed}
                        className="h-8 text-xs font-mono bg-slate-900 border-slate-800"
                      />
                    </div>
                    <div>
                      <span className="text-[11px] text-slate-500">IGST</span>
                      <Input
                        value={editIgst}
                        onChange={(e) => setEditIgst(e.target.value)}
                        disabled={isConfirmed}
                        className="h-8 text-xs font-mono bg-slate-900 border-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* Line Items Table if Present */}
                {latestExtraction?.structured_data?.line_items &&
                  latestExtraction.structured_data.line_items.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <span className="text-xs font-semibold text-slate-300">Extracted Line Items</span>
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                            <tr>
                              <th className="p-2.5">Item Description</th>
                              <th className="p-2.5 text-center">Qty</th>
                              <th className="p-2.5 text-right">Price</th>
                              <th className="p-2.5 text-right">Amount</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 bg-slate-900/50">
                            {latestExtraction.structured_data.line_items.map((item, idx) => (
                              <tr key={idx}>
                                <td className="p-2.5 text-slate-200">{item.description}</td>
                                <td className="p-2.5 text-center text-slate-400">{item.quantity}</td>
                                <td className="p-2.5 text-right font-mono text-slate-400">
                                  ₹{item.unit_price}
                                </td>
                                <td className="p-2.5 text-right font-mono font-medium text-slate-200">
                                  ₹{item.amount}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                {!isConfirmed && (
                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" size="sm" onClick={handleSaveCorrections}>
                      Save Field Corrections
                    </Button>
                  </div>
                )}
              </Card>

              {/* Transaction Match Candidates Card */}
              {matches.length > 0 && !isConfirmed && (
                <Card className="p-4 bg-slate-900 border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                      <CreditCard className="h-4 w-4 text-amber-400" />
                      Matching Existing Transactions ({matches.length})
                    </h4>
                    <span className="text-xs text-slate-400">
                      Found corresponding transactions in workspace
                    </span>
                  </div>

                  <div className="space-y-2">
                    {matches.map((m) => (
                      <div
                        key={m.transaction_id}
                        className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between"
                      >
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-semibold text-slate-200">
                              {m.transaction_summary.description}
                            </span>
                            <Badge
                              variant={m.match_status === 'exact' ? 'income' : 'warning'}
                              size="sm"
                            >
                              {m.match_status.toUpperCase()} ({Math.round(Number(m.match_score) * 100)}%)
                            </Badge>
                          </div>
                          <p className="text-[11px] text-slate-400">
                            {m.transaction_summary.transaction_date} • ₹{m.transaction_summary.amount} •{' '}
                            {m.transaction_summary.direction}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleAssociateMatch(m)}
                          className="text-xs flex items-center gap-1.5"
                        >
                          <Check className="h-3.5 w-3.5" /> Link Receipt
                        </Button>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Confirmation Gate Card */}
              {!isConfirmed && !isRejected && (
                <Card className="p-5 bg-gradient-to-r from-slate-900 to-indigo-950/40 border-indigo-500/30 space-y-4">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-indigo-400" />
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        Explicit Confirmation & Ledger Creation Gate
                      </h4>
                      <p className="text-xs text-slate-400">
                        OCR extractions are untrusted until you verify. Confirming posts an authoritative financial transaction.
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                    <div className="flex-1">
                      <select
                        aria-label="Target account for ledger posting"
                        value={selectedAccountId}
                        onChange={(e) => setSelectedAccountId(e.target.value)}
                        className="w-full h-10 px-3 text-sm bg-slate-950 border border-slate-700 rounded-lg text-white"
                      >
                        <option value="" disabled>
                          Select Debit Financial Account...
                        </option>
                        {accounts.map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.name} ({acc.account_type}) - ₹
                            {(acc.current_book_balance_paise / 100).toFixed(2)}
                          </option>
                        ))}
                      </select>
                    </div>

                    <Button
                      variant="primary"
                      onClick={handleConfirmAndPost}
                      disabled={!selectedAccountId || !editTotal || Number(editTotal) <= 0}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-2"
                    >
                      <Check className="h-4 w-4" />
                      Confirm & Post Transaction
                    </Button>

                    <Button
                      variant="outline"
                      onClick={handleReject}
                      className="text-rose-400 border-rose-500/30 hover:bg-rose-500/10"
                    >
                      Reject
                    </Button>
                  </div>
                </Card>
              )}

              {/* Already Confirmed Banner */}
              {isConfirmed && (
                <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                    <span className="text-sm font-medium">
                      This document has been verified and posted to the authoritative ledger.
                    </span>
                  </div>
                  {selectedDocument.transaction_associations &&
                    selectedDocument.transaction_associations.length > 0 && (
                      <span className="text-xs font-mono text-emerald-400">
                        Tx: {selectedDocument.transaction_associations[0].transaction_id.slice(0, 8)}...
                      </span>
                    )}
                </div>
              )}
            </div>
          ) : (
            <Card className="p-12 text-center bg-slate-900/60 border-slate-800 space-y-3">
              <div className="h-14 w-14 rounded-2xl bg-slate-800/80 flex items-center justify-center text-slate-400 mx-auto">
                <FileText className="h-7 w-7" />
              </div>
              <h3 className="text-base font-semibold text-slate-200">Select a document to review</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Choose an uploaded receipt or invoice from the list on the left to inspect OCR results,
                verify GST details, correct fields, or post an authoritative transaction.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
