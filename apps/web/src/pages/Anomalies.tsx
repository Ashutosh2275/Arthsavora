import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RefreshCw,
  Search,
  Filter,
  Eye,
  Sliders,
  Plus,
  Trash2,
  ArrowUpRight,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import type {
  AnomalyDetectionResponse,
  AnomalyReviewRequest,
  AnomalySeverity,
  DetectionExceptionCreateRequest,
} from '@arthsavora/contracts';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FinancialAmount } from '@/components/ui/financial-amount';
import { Modal } from '@/components/ui/modal';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useAnomalyStore } from '@/store/useAnomalyStore';

export function Anomalies() {
  const {
    anomalies,
    summary,
    rules,
    exceptions,
    statusFilter,
    severityFilter,
    isLoading,
    error,
    setStatusFilter,
    setSeverityFilter,
    fetchAnomalies,
    fetchSummary,
    fetchRules,
    fetchExceptions,
    scanRecentTransactions,
    reviewAnomaly,
    acknowledgeAnomaly,
    dismissAnomaly,
    updateRule,
    createException,
    deleteException,
  } = useAnomalyStore();

  const [activeTab, setActiveTab] = useState<'feed' | 'rules' | 'exceptions'>('feed');
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyDetectionResponse | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<string>('acknowledge');
  const [reviewReason, setReviewReason] = useState<string>('');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [createWhitelistException, setCreateWhitelistException] = useState<boolean>(false);
  const [exceptionDurationDays, setExceptionDurationDays] = useState<number>(90);

  // New Exception Modal state
  const [isAddExceptionModalOpen, setIsAddExceptionModalOpen] = useState(false);
  const [newExcReason, setNewExcReason] = useState('');
  const [newExcPattern, setNewExcPattern] = useState('');
  const [newExcMaxAmount, setNewExcMaxAmount] = useState('');

  useEffect(() => {
    fetchAnomalies();
    fetchSummary();
    fetchRules();
    fetchExceptions();
  }, [fetchAnomalies, fetchSummary, fetchRules, fetchExceptions]);

  const handleOpenReview = (anomaly: AnomalyDetectionResponse) => {
    setSelectedAnomaly(anomaly);
    setReviewAction('acknowledge');
    setReviewReason('');
    setReviewNotes('');
    setCreateWhitelistException(false);
    setIsReviewModalOpen(true);
  };

  const handleReviewSubmit = async () => {
    if (!selectedAnomaly) return;
    const req: AnomalyReviewRequest = {
      action: reviewAction,
      reason: reviewReason || undefined,
      notes: reviewNotes || undefined,
      create_exception: createWhitelistException,
      exception_expires_in_days: createWhitelistException ? exceptionDurationDays : undefined,
    };
    await reviewAnomaly(selectedAnomaly.id, req);
    setIsReviewModalOpen(false);
  };

  const handleAddExceptionSubmit = async () => {
    if (!newExcReason.trim()) return;
    const req: DetectionExceptionCreateRequest = {
      reason: newExcReason.trim(),
      merchant_name_pattern: newExcPattern.trim() || undefined,
      max_amount_paise: newExcMaxAmount ? Math.round(parseFloat(newExcMaxAmount) * 100) : undefined,
    };
    await createException(req);
    setIsAddExceptionModalOpen(false);
    setNewExcReason('');
    setNewExcPattern('');
    setNewExcMaxAmount('');
  };

  const getSeverityBadgeVariant = (sev: string): 'expense' | 'warning' | 'brand' | 'info' | 'neutral' => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'expense';
      case 'high':
        return 'warning';
      case 'medium':
        return 'brand';
      case 'low':
        return 'info';
      default:
        return 'neutral';
    }
  };

  const getStatusBadgeVariant = (st: string): 'income' | 'warning' | 'expense' | 'brand' | 'info' | 'neutral' => {
    switch (st.toLowerCase()) {
      case 'new':
        return 'warning';
      case 'under_review':
        return 'brand';
      case 'acknowledged':
        return 'info';
      case 'expected_activity':
        return 'income';
      case 'escalated':
        return 'expense';
      case 'dismissed':
      default:
        return 'neutral';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="h-7 w-7 text-indigo-400" />
            Financial Security & Risk Intelligence
          </h1>
          <p className="text-sm text-slate-400">
            Explainable anomaly detection, fraud signals, and risk monitoring without alarmist claims.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => scanRecentTransactions(7, false)}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Scan Recent Transactions
          </Button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Open Anomalies</p>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{summary?.open_anomalies ?? 0}</span>
            <Badge variant="warning" size="sm">Action Required</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">Pending user review or confirmation</p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">High / Critical Risk</p>
            <ShieldAlert className="h-4 w-4 text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{summary?.high_severity_anomalies ?? 0}</span>
            <Badge variant="expense" size="sm">Elevated</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">Exceeding high risk deviation thresholds</p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Average Risk Score</p>
            <TrendingUp className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{summary?.average_risk_score ?? 0}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Across all open active detections</p>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Resolved / Dismissed</p>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{summary?.resolved_anomalies ?? 0}</span>
            <Badge variant="income" size="sm">Reviewed</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-1">Confirmed expected or cleared by user</p>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('feed')}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'feed'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          Anomaly Feed ({anomalies.length})
        </button>
        <button
          onClick={() => setActiveTab('rules')}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'rules'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="h-4 w-4" />
          Detection Rules ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab('exceptions')}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'exceptions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <CheckCircle2 className="h-4 w-4" />
          Whitelist Exceptions ({exceptions.length})
        </button>
      </div>

      {/* TAB 1: ANOMALY FEED */}
      {activeTab === 'feed' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-400 flex items-center gap-1 font-medium mr-1">
                <Filter className="h-3.5 w-3.5" /> Filter by:
              </span>
              <button
                onClick={() => setStatusFilter(null)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  statusFilter === null
                    ? 'bg-indigo-600 border-indigo-500 text-white font-medium'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                }`}
              >
                All Status
              </button>
              {['new', 'under_review', 'acknowledged', 'expected_activity', 'dismissed'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`text-xs px-2.5 py-1 rounded-full border capitalize transition-colors ${
                    statusFilter === st
                      ? 'bg-indigo-600 border-indigo-500 text-white font-medium'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Severity:</span>
              <select
                value={severityFilter || ''}
                onChange={(e) => setSeverityFilter(e.target.value || null)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 outline-none focus:border-indigo-500"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="informational">Informational</option>
              </select>
            </div>
          </div>

          {/* Anomaly Cards List */}
          {anomalies.length === 0 ? (
            <Card className="p-12 text-center bg-slate-900/40 border-slate-800">
              <ShieldCheck className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-white">No Anomalies Detected</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
                All recent financial activity aligns with normal baseline behavior, merchant frequency patterns, and recurring schedules.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => scanRecentTransactions(14, true)}
                className="mt-4"
              >
                Run In-Depth 14-Day Scan
              </Button>
            </Card>
          ) : (
            <div className="space-y-3">
              {anomalies.map((a) => (
                <Card
                  key={a.id}
                  className="p-4 bg-slate-900/60 border-slate-800 hover:border-slate-700 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={getSeverityBadgeVariant(a.severity)} size="sm">
                        {a.severity.toUpperCase()}
                      </Badge>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                        Score: {a.risk_score}/100
                      </span>
                      <Badge variant={getStatusBadgeVariant(a.status)} size="sm">
                        {a.status.replace('_', ' ').toUpperCase()}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        Method: <strong className="text-slate-300 font-mono">{a.detection_method}</strong>
                      </span>
                      <span className="text-xs text-slate-500">
                        • {new Date(a.detected_at).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-sm font-medium text-slate-200">
                      {a.explanation}
                    </p>

                    {a.transaction && (
                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                        <span>
                          Merchant: <strong className="text-white">{a.transaction.merchant_name || a.transaction.description}</strong>
                        </span>
                        <span>
                          Amount:{' '}
                          <FinancialAmount
                            amount={a.transaction.amount_paise / 100}
                            currency={a.transaction.currency}
                            showSign={false}
                            className="font-bold text-white"
                          />
                        </span>
                        <span>
                          Date: <span className="text-slate-300">{a.transaction.transaction_date}</span>
                        </span>
                        {a.transaction.category_name && (
                          <span>
                            Category: <span className="text-indigo-400">{a.transaction.category_name}</span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenReview(a)}
                      className="text-xs"
                    >
                      Review
                    </Button>
                    {a.status === 'new' && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => acknowledgeAnomaly(a.id)}
                          className="text-xs text-slate-300 hover:text-white"
                        >
                          Acknowledge
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => dismissAnomaly(a.id, 'Dismissed from feed')}
                          className="text-xs text-slate-400 hover:text-rose-400"
                        >
                          Dismiss
                        </Button>
                      </>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: DETECTION RULES */}
      {activeTab === 'rules' && (
        <div className="space-y-4">
          <div className="bg-slate-900/40 p-4 rounded-lg border border-slate-800 text-sm text-slate-300">
            <p className="font-semibold text-white">Deterministic Anomaly Detection Rules</p>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic rules execute before statistical and machine learning models. Toggle rules or calibrate workspace-specific thresholds.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rules.map((r) => (
              <Card key={r.id} className="p-4 bg-slate-900/60 border-slate-800 flex flex-col justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-white">{r.name}</h4>
                    <Switch
                      checked={r.is_enabled}
                      onChange={(checked: boolean) => updateRule(r.id, { is_enabled: checked })}
                    />
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{r.description}</p>
                  <div className="flex items-center gap-2 pt-1">
                    <Badge variant="neutral" size="sm">Code: {r.rule_code}</Badge>
                    <Badge variant={getSeverityBadgeVariant(r.severity)} size="sm">
                      {r.severity.toUpperCase()}
                    </Badge>
                  </div>
                </div>

                <div className="text-xs bg-slate-950/60 p-2.5 rounded border border-slate-800 font-mono text-slate-300">
                  <p className="text-[10px] uppercase text-slate-500 font-bold mb-1">Configuration:</p>
                  {JSON.stringify(r.threshold_config, null, 2)}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: WHITELIST EXCEPTIONS */}
      {activeTab === 'exceptions' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-lg border border-slate-800">
            <div>
              <p className="text-sm font-semibold text-white">Detection Whitelist Exceptions</p>
              <p className="text-xs text-slate-400">
                Suppress anomaly alerts for verified high-value recurring merchants, tuition fees, or contractor payouts.
              </p>
            </div>
            <Button
              size="sm"
              onClick={() => setIsAddExceptionModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" /> Add Exception
            </Button>
          </div>

          {exceptions.length === 0 ? (
            <Card className="p-8 text-center bg-slate-900/40 border-slate-800">
              <CheckCircle2 className="h-10 w-10 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No Whitelist Exceptions Configured</p>
              <p className="text-xs text-slate-500 mt-1">
                You can add exceptions here or directly whitelist entities during anomaly review.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {exceptions.map((exc) => (
                <Card
                  key={exc.id}
                  className="p-4 bg-slate-900/60 border-slate-800 flex items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white">
                        {exc.merchant_name || exc.merchant_name_pattern || 'Custom Whitelist Rule'}
                      </span>
                      {exc.expires_at ? (
                        <Badge variant="neutral" size="sm">Expires: {exc.expires_at}</Badge>
                      ) : (
                        <Badge variant="income" size="sm">Permanent</Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-300">Reason: {exc.reason}</p>
                    {exc.max_amount_paise && (
                      <p className="text-xs text-slate-500">
                        Amount Ceiling: <FinancialAmount amount={exc.max_amount_paise / 100} currency="INR" showSign={false} />
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteException(exc.id)}
                    className="text-slate-400 hover:text-rose-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ANOMALY REVIEW MODAL */}
      {isReviewModalOpen && selectedAnomaly && (
        <Modal
          isOpen={isReviewModalOpen}
          onClose={() => setIsReviewModalOpen(false)}
          title="Review Financial Anomaly"
          description="Evaluate flagged transaction pattern and select review action."
        >
          <div className="space-y-4">
            {/* Transaction summary card */}
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Transaction:</span>
                <span className="font-bold text-white">
                  {selectedAnomaly.transaction?.merchant_name || selectedAnomaly.transaction?.description}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Amount:</span>
                {selectedAnomaly.transaction && (
                  <FinancialAmount
                    amount={selectedAnomaly.transaction.amount_paise / 100}
                    currency={selectedAnomaly.transaction.currency}
                    className="font-bold text-rose-400"
                  />
                )}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Risk Score:</span>
                <span className="font-bold text-indigo-400">{selectedAnomaly.risk_score} / 100</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Detection Method:</span>
                <span className="font-mono text-slate-300">{selectedAnomaly.detection_method}</span>
              </div>
            </div>

            {/* Explanation */}
            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs text-slate-200">
              <p className="font-semibold text-white mb-1">Reason for Detection:</p>
              <p>{selectedAnomaly.explanation}</p>
            </div>

            {/* Action selector */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Review Decision:</label>
              <select
                value={reviewAction}
                onChange={(e) => setReviewAction(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5 outline-none focus:border-indigo-500"
              >
                <option value="mark_expected">Mark as Expected Activity (Legitimate)</option>
                <option value="acknowledge">Acknowledge (Noted, Keep in Records)</option>
                <option value="mark_suspicious">Mark as Suspicious / Escalate</option>
                <option value="dismiss">Dismiss Alert (Non-actionable)</option>
              </select>
            </div>

            {/* Whitelist exception checkbox */}
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="whitelist-chk"
                  checked={createWhitelistException}
                  onChange={(e) => setCreateWhitelistException(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="whitelist-chk" className="text-xs font-medium text-slate-300 cursor-pointer">
                  Whitelist this merchant / category (Don't flag similar payments)
                </label>
              </div>

              {createWhitelistException && (
                <div className="pt-2 flex items-center gap-2 text-xs text-slate-400">
                  <span>Duration:</span>
                  <select
                    value={exceptionDurationDays}
                    onChange={(e) => setExceptionDurationDays(Number(e.target.value))}
                    className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1"
                  >
                    <option value={30}>30 Days</option>
                    <option value={90}>90 Days</option>
                    <option value={180}>180 Days</option>
                    <option value={365}>1 Year</option>
                  </select>
                </div>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Review Notes (Optional):</label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Add context or notes for audit trail..."
                rows={2}
                className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2.5 outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setIsReviewModalOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleReviewSubmit}>
                Confirm Review
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ADD EXCEPTION MODAL */}
      {isAddExceptionModalOpen && (
        <Modal
          isOpen={isAddExceptionModalOpen}
          onClose={() => setIsAddExceptionModalOpen(false)}
          title="Create Whitelist Exception"
          description="Specify merchant name pattern and ceiling amounts to suppress anomaly alerts."
        >
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Merchant Name / Pattern:</label>
              <Input
                value={newExcPattern}
                onChange={(e) => setNewExcPattern(e.target.value)}
                placeholder="e.g. Swiggy, Bescom, Tuition"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Maximum Allowed Amount (₹):</label>
              <Input
                type="number"
                value={newExcMaxAmount}
                onChange={(e) => setNewExcMaxAmount(e.target.value)}
                placeholder="e.g. 50000"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300">Reason for Whitelist:</label>
              <Input
                value={newExcReason}
                onChange={(e) => setNewExcReason(e.target.value)}
                placeholder="e.g. Verified university tuition payment"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setIsAddExceptionModalOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleAddExceptionSubmit} disabled={!newExcReason.trim()}>
                Save Exception
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
