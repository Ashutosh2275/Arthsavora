import React, { useEffect, useState } from 'react';
import {
  FileText,
  Download,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Scale,
  ShieldCheck,
  RefreshCw,
  Calendar,
  Layers,
  Sparkles,
  Info,
  Check,
  Building,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { useFinancialReportStore } from '@/store/useFinancialReportStore';
import type {
  AccountingBasis,
  FinancialReportType,
  TaxRegime,
  TaxReviewStatus,
} from '@arthsavora/contracts';

type ActiveTab =
  | 'statements'
  | 'cash_flow'
  | 'balance_sheet'
  | 'tax_intelligence'
  | 'gst_readiness'
  | 'tax_estimator'
  | 'validations'
  | 'history';

export const FinancialReports: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('statements');

  const {
    periods,
    selectedPeriod,
    accountingBasis,
    incomeStatement,
    cashFlowStatement,
    balanceSheet,
    trialBalance,
    generatedReports,
    taxClassifications,
    gstSummary,
    taxEstimate,
    validationFindings,
    isLoading,
    error,
    clearError,
    setSelectedPeriod,
    setAccountingBasis,
    fetchPeriods,
    fetchIncomeStatement,
    fetchCashFlowStatement,
    fetchBalanceSheet,
    fetchTrialBalance,
    generateReportSnapshot,
    fetchReportHistory,
    downloadReportCSV,
    fetchValidations,
    resolveValidation,
    fetchTaxClassifications,
    suggestTaxClassifications,
    reviewTaxClassification,
    fetchGSTSummary,
    fetchTaxEstimate,
    createTaxEstimate,
  } = useFinancialReportStore();

  // Review modal state
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [reviewCategory, setReviewCategory] = useState<string>('section_80c');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [reviewDeductible, setReviewDeductible] = useState<number>(0);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  // Regime switcher
  const [selectedRegime, setSelectedRegime] = useState<TaxRegime>('new_regime');

  useEffect(() => {
    fetchPeriods();
    fetchReportHistory();
    fetchValidations();
  }, []);

  useEffect(() => {
    if (selectedPeriod) {
      if (activeTab === 'statements') {
        fetchIncomeStatement(selectedPeriod.period_type, selectedPeriod.fiscal_year, selectedPeriod.quarter || undefined, accountingBasis);
      } else if (activeTab === 'cash_flow') {
        fetchCashFlowStatement(selectedPeriod.period_type, selectedPeriod.fiscal_year, selectedPeriod.quarter || undefined);
      } else if (activeTab === 'balance_sheet') {
        fetchBalanceSheet(selectedPeriod.end_date);
        fetchTrialBalance(selectedPeriod.end_date);
      } else if (activeTab === 'tax_intelligence') {
        fetchTaxClassifications(selectedPeriod.fiscal_year);
      } else if (activeTab === 'gst_readiness') {
        fetchGSTSummary(selectedPeriod.period_type, selectedPeriod.fiscal_year, selectedPeriod.quarter || undefined);
      } else if (activeTab === 'tax_estimator') {
        fetchTaxEstimate(selectedPeriod.fiscal_year);
      } else if (activeTab === 'validations') {
        fetchValidations(selectedPeriod.fiscal_year);
      }
    }
  }, [selectedPeriod, accountingBasis, activeTab]);

  const handleGenerateSnapshot = async (reportType: FinancialReportType) => {
    if (!selectedPeriod) return;
    try {
      await generateReportSnapshot({
        report_type: reportType,
        period_type: selectedPeriod.period_type,
        fiscal_year: selectedPeriod.fiscal_year,
        quarter: selectedPeriod.quarter || undefined,
        basis: accountingBasis,
        format: 'csv',
      });
      toast.success(`${reportType.replace('_', ' ').toUpperCase()} snapshot generated and verified.`);
      fetchReportHistory();
    } catch (err: any) {
      toast.error(err.message || 'Failed to generate report snapshot');
    }
  };

  const handleDownloadCSV = async (reportId: string, title: string) => {
    await downloadReportCSV(reportId, `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.csv`);
    toast.success('Report CSV exported with formula-injection sanitization.');
  };

  const handleScanTaxSuggestions = async () => {
    if (!selectedPeriod) return;
    try {
      await suggestTaxClassifications(selectedPeriod.fiscal_year);
      toast.success('Automated tax classification scan complete.');
    } catch (err: any) {
      toast.error('Failed to run tax suggestions scan.');
    }
  };

  const openReviewModal = (txId: string, category: string, deductiblePaise: number, notes?: string) => {
    setSelectedTxId(txId);
    setReviewCategory(category || 'section_80c');
    setReviewDeductible(deductiblePaise ? deductiblePaise / 100 : 0);
    setReviewNotes(notes || '');
    setIsReviewModalOpen(true);
  };

  const handleConfirmReview = async () => {
    if (!selectedTxId) return;
    try {
      await reviewTaxClassification(selectedTxId, {
        tax_category: reviewCategory,
        review_status: 'confirmed',
        deductible_amount_paise: Math.round(reviewDeductible * 100),
        notes: reviewNotes,
      });
      toast.success('Tax classification confirmed.');
      setIsReviewModalOpen(false);
      setSelectedTxId(null);
    } catch (err: any) {
      toast.error('Failed to confirm tax classification.');
    }
  };

  const handleCalculateEstimate = async (regime: TaxRegime) => {
    if (!selectedPeriod) return;
    try {
      await createTaxEstimate({
        financial_year: selectedPeriod.fiscal_year,
        regime,
      });
      toast.success(`Calculated estimate under ${regime === 'new_regime' ? 'New' : 'Old'} Regime.`);
    } catch (err: any) {
      toast.error('Failed to calculate income tax estimate.');
    }
  };

  const handleResolveFinding = async (findingId: string) => {
    try {
      await resolveValidation(findingId, 'Audited and marked resolved by user');
      toast.success('Validation finding marked as resolved.');
    } catch {
      toast.error('Failed to resolve finding.');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <FileText className="text-indigo-400" size={26} /> Financial Reports & Tax Intelligence
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Verified financial statements, Indian Financial Year reporting, GST readiness, and mathematical tax intelligence.
          </p>
        </div>

        {/* Global Period & Basis Selector */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Period Selector */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300">
            <Calendar size={14} className="text-indigo-400" />
            <select
              aria-label="Select Period"
              className="bg-transparent text-white text-xs focus:outline-none cursor-pointer"
              value={selectedPeriod?.label || ''}
              onChange={(e) => {
                const found = periods.find((p) => p.label === e.target.value);
                if (found) setSelectedPeriod(found);
              }}
            >
              {periods.map((p) => (
                <option key={p.label} value={p.label} className="bg-slate-900 text-white">
                  {p.label} ({p.start_date} to {p.end_date})
                </option>
              ))}
            </select>
          </div>

          {/* Basis Toggle */}
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5 text-xs">
            <button
              onClick={() => setAccountingBasis('cash')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                accountingBasis === 'cash'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Cash Basis
            </button>
            <button
              onClick={() => setAccountingBasis('accrual')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                accountingBasis === 'accrual'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Accrual Basis
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-slate-800 pb-2">
        {[
          { id: 'statements', label: 'Income & Expense', icon: <TrendingUp size={14} /> },
          { id: 'cash_flow', label: 'Cash Flow', icon: <DollarSign size={14} /> },
          { id: 'balance_sheet', label: 'Balance Sheet & Trial Balance', icon: <Scale size={14} /> },
          { id: 'tax_intelligence', label: 'Tax Classifications', icon: <ShieldCheck size={14} /> },
          { id: 'gst_readiness', label: 'GST Readiness', icon: <Building size={14} /> },
          { id: 'tax_estimator', label: 'Income Tax Estimator', icon: <Sparkles size={14} /> },
          { id: 'validations', label: 'Validation Center', icon: <AlertTriangle size={14} /> },
          { id: 'history', label: 'Report Snapshots', icon: <Layers size={14} /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as ActiveTab)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Income and Expense Statement */}
      {activeTab === 'statements' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Income and Expense Statement</h2>
              <p className="text-xs text-slate-400">
                Operating results reported under {accountingBasis.toUpperCase()} accounting basis for {selectedPeriod?.label}.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => handleGenerateSnapshot('income_statement')}
            >
              <Download size={14} /> Snapshot & Export CSV
            </Button>
          </div>

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Total Revenue / Inflow</span>
              <p className="text-xl font-bold text-emerald-400 mt-1">
                ₹{((incomeStatement?.total_income_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">
                {incomeStatement?.income_lines.length || 0} revenue account streams
              </span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Total Operating Expenses</span>
              <p className="text-xl font-bold text-rose-400 mt-1">
                ₹{((incomeStatement?.total_expense_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">
                {incomeStatement?.expense_lines.length || 0} expense categories
              </span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Net Operating Surplus / (Deficit)</span>
              <p
                className={`text-xl font-bold mt-1 ${
                  (incomeStatement?.net_surplus_deficit_paise || 0) >= 0 ? 'text-indigo-400' : 'text-amber-400'
                }`}
              >
                ₹{((incomeStatement?.net_surplus_deficit_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">
                {(incomeStatement?.net_surplus_deficit_paise || 0) >= 0 ? 'Net Operating Savings' : 'Operating Deficit'}
              </span>
            </Card>
          </div>

          {/* Statement Lines Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Inflows */}
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-1.5 mb-3">
                <TrendingUp size={16} /> Revenue & Inflow Breakdown
              </h3>
              <div className="divide-y divide-slate-800 text-xs">
                {incomeStatement?.income_lines.map((line, idx) => (
                  <div key={idx} className="py-2.5 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-slate-200">{line.account_name}</p>
                      <span className="text-[10px] text-slate-500 font-mono">{line.account_code}</span>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-white">
                        ₹{(line.balance_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </p>
                      <span className="text-[10px] text-slate-400">{line.percentage_of_total.toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
                {(!incomeStatement?.income_lines || incomeStatement.income_lines.length === 0) && (
                  <p className="text-xs text-slate-500 py-4 text-center">No revenue lines found for this period.</p>
                )}
              </div>
            </Card>

            {/* Outflows */}
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-rose-400 flex items-center gap-1.5 mb-3">
                <TrendingDown size={16} /> Expenses & Outflow Breakdown
              </h3>
              <div className="divide-y divide-slate-800 text-xs">
                {incomeStatement?.expense_lines.map((line, idx) => (
                  <div key={idx} className="py-2.5 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-slate-200">{line.account_name}</p>
                      <span className="text-[10px] text-slate-500 font-mono">{line.account_code}</span>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-white">
                        ₹{(line.balance_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </p>
                      <span className="text-[10px] text-slate-400">{line.percentage_of_total.toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
                {(!incomeStatement?.expense_lines || incomeStatement.expense_lines.length === 0) && (
                  <p className="text-xs text-slate-500 py-4 text-center">No expense lines recorded for this period.</p>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Cash Flow Statement */}
      {activeTab === 'cash_flow' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Cash Flow Statement</h2>
              <p className="text-xs text-slate-400">
                Operating, investing, and financing cash movements excluding internal bank transfers.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => handleGenerateSnapshot('cash_flow')}
            >
              <Download size={14} /> Snapshot & Export CSV
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Opening Liquid Cash</span>
              <p className="text-xl font-bold text-white mt-1">
                ₹{((cashFlowStatement?.opening_cash_balance_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">At period start ({selectedPeriod?.start_date})</span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Net Period Cash Change</span>
              <p
                className={`text-xl font-bold mt-1 ${
                  (cashFlowStatement?.net_cash_change_paise || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                ₹{((cashFlowStatement?.net_cash_change_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">Net operating + investing + financing</span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Closing Liquid Balance</span>
              <p className="text-xl font-bold text-indigo-400 mt-1">
                ₹{((cashFlowStatement?.closing_cash_balance_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">At period end ({selectedPeriod?.end_date})</span>
            </Card>
          </div>

          <Card className="p-4 border-slate-800 bg-slate-900/40">
            <h3 className="text-sm font-semibold text-white mb-3">Cash Activity Summary</h3>
            <div className="divide-y divide-slate-800 text-xs">
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-300">Net Cash Flow from Operating Activities</span>
                <span className="font-semibold text-white">
                  ₹{((cashFlowStatement?.net_operating_cash_flow_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-300">Net Cash Flow from Investing Activities</span>
                <span className="font-semibold text-white">
                  ₹{((cashFlowStatement?.net_investing_cash_flow_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-300">Net Cash Flow from Financing Activities</span>
                <span className="font-semibold text-white">
                  ₹{((cashFlowStatement?.net_financing_cash_flow_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 3: Balance Sheet & Trial Balance */}
      {activeTab === 'balance_sheet' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Balance Sheet & Trial Balance</h2>
              <p className="text-xs text-slate-400">
                Point-in-time financial position verifying the fundamental accounting equation Assets = Liabilities + Equity.
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => handleGenerateSnapshot('balance_sheet')}
              >
                <Download size={14} /> Balance Sheet CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs"
                onClick={() => handleGenerateSnapshot('trial_balance')}
              >
                <Download size={14} /> Trial Balance CSV
              </Button>
            </div>
          </div>

          {/* Equation Health Indicator */}
          <div
            className={`p-4 rounded-xl border flex items-center justify-between ${
              balanceSheet?.is_balanced
                ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
                : 'bg-rose-950/20 border-rose-800/40 text-rose-300'
            }`}
          >
            <div className="flex items-center gap-3">
              {balanceSheet?.is_balanced ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
              <div>
                <p className="font-bold text-sm">
                  {balanceSheet?.is_balanced ? 'Balance Sheet Equation Balanced (Assets = Liabilities + Equity)' : 'Balance Sheet Discrepancy Detected'}
                </p>
                <p className="text-xs opacity-80 mt-0.5">
                  Assets: ₹{((balanceSheet?.total_assets_paise || 0) / 100).toLocaleString('en-IN')} |
                  Liabilities + Equity: ₹{(((balanceSheet?.total_liabilities_paise || 0) + (balanceSheet?.total_equity_paise || 0)) / 100).toLocaleString('en-IN')}
                </p>
              </div>
            </div>
            {!balanceSheet?.is_balanced && (
              <Badge variant="expense" className="text-xs">
                Variance: ₹{((balanceSheet?.discrepancy_paise || 0) / 100).toLocaleString('en-IN')}
              </Badge>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Assets */}
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-emerald-400 mb-2">Assets</h3>
              <p className="text-lg font-bold text-white mb-3">
                ₹{((balanceSheet?.total_assets_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <div className="divide-y divide-slate-800 text-xs">
                {balanceSheet?.asset_lines.map((l, i) => (
                  <div key={i} className="py-2 flex justify-between">
                    <span className="text-slate-300">{l.account_name}</span>
                    <span className="font-medium text-white">₹{(l.balance_paise / 100).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Liabilities */}
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-rose-400 mb-2">Liabilities</h3>
              <p className="text-lg font-bold text-white mb-3">
                ₹{((balanceSheet?.total_liabilities_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <div className="divide-y divide-slate-800 text-xs">
                {balanceSheet?.liability_lines.map((l, i) => (
                  <div key={i} className="py-2 flex justify-between">
                    <span className="text-slate-300">{l.account_name}</span>
                    <span className="font-medium text-white">₹{(l.balance_paise / 100).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Equity */}
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-indigo-400 mb-2">Equity & Retained Earnings</h3>
              <p className="text-lg font-bold text-white mb-3">
                ₹{((balanceSheet?.total_equity_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <div className="divide-y divide-slate-800 text-xs">
                {balanceSheet?.equity_lines.map((l, i) => (
                  <div key={i} className="py-2 flex justify-between">
                    <span className="text-slate-300">{l.account_name}</span>
                    <span className="font-medium text-white">₹{(l.balance_paise / 100).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Trial Balance Section */}
          <Card className="p-4 border-slate-800 bg-slate-900/40">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white">Trial Balance Audit</h3>
              <span className={`text-xs font-medium ${trialBalance?.is_balanced ? 'text-emerald-400' : 'text-rose-400'}`}>
                {trialBalance?.is_balanced ? 'Total Debits == Total Credits' : 'Debit/Credit Imbalance Detected'}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2">Code</th>
                    <th className="py-2">Account Name</th>
                    <th className="py-2">Type</th>
                    <th className="py-2 text-right">Debit Balance</th>
                    <th className="py-2 text-right">Credit Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {trialBalance?.lines.map((line, i) => (
                    <tr key={i}>
                      <td className="py-2 font-mono text-slate-500">{line.account_code}</td>
                      <td className="py-2 font-medium">{line.account_name}</td>
                      <td className="py-2 text-slate-400 capitalize">{line.account_type}</td>
                      <td className="py-2 text-right text-emerald-400">
                        {['asset', 'expense'].includes(line.account_type)
                          ? `₹${(line.balance_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                          : '-'}
                      </td>
                      <td className="py-2 text-right text-indigo-400">
                        {['liability', 'equity', 'revenue'].includes(line.account_type)
                          ? `₹${(line.balance_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 4: Tax Intelligence & Classification */}
      {activeTab === 'tax_intelligence' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Tax Intelligence & Transaction Classification</h2>
              <p className="text-xs text-slate-400">
                Categorize income and deductions for Indian Income Tax compliance (Section 80C, 80D, business opex).
              </p>
            </div>
            <Button size="sm" className="gap-1.5 text-xs" onClick={handleScanTaxSuggestions}>
              <RefreshCw size={14} /> Scan & Auto-Suggest Rules
            </Button>
          </div>

          <Card className="border-slate-800 bg-slate-900/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Tax Year</th>
                    <th className="py-3 px-4">Tax Category</th>
                    <th className="py-3 px-4">Rule Code</th>
                    <th className="py-3 px-4 text-right">Taxable (₹)</th>
                    <th className="py-3 px-4 text-right">Deductible (₹)</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {taxClassifications.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/20">
                      <td className="py-3 px-4 font-mono text-slate-400">{item.tax_year}</td>
                      <td className="py-3 px-4 font-medium text-white capitalize">
                        {item.tax_category.replace(/_/g, ' ')}
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-mono">{item.rule_code || 'MANUAL'}</td>
                      <td className="py-3 px-4 text-right">
                        ₹{(item.taxable_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-emerald-400">
                        ₹{(item.deductible_amount_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={item.review_status === 'confirmed' ? 'brand' : 'neutral'}
                          className="capitalize text-[10px]"
                        >
                          {item.review_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-indigo-400 hover:text-indigo-300 text-xs"
                          onClick={() =>
                            openReviewModal(
                              item.transaction_id,
                              item.tax_category,
                              item.deductible_amount_paise,
                              item.user_notes || ''
                            )
                          }
                        >
                          Review
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {taxClassifications.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-slate-500 text-xs">
                        No transactions classified for this financial year yet. Click &quot;Scan & Auto-Suggest Rules&quot; to begin.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 5: GST Readiness */}
      {activeTab === 'gst_readiness' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">GST Readiness & Turnover Summary</h2>
              <p className="text-xs text-slate-400">
                Turnover and output tax metrics compiled directly from issued commercial invoices.
              </p>
            </div>
          </div>

          {/* Statutory Disclaimer Alert */}
          <div className="p-4 rounded-xl border border-amber-800/40 bg-amber-950/20 text-amber-300 text-xs flex items-start gap-3">
            <Info size={18} className="shrink-0 mt-0.5 text-amber-400" />
            <div>
              <p className="font-semibold text-amber-200">Statutory Notice & Scope Limitation</p>
              <p className="mt-1 leading-relaxed opacity-90">
                {gstSummary?.disclaimer ||
                  'ARTHSAVORA provides informational business record summaries. This report is NOT an official GST return filing (GSTR-1, GSTR-3B) or certified audit.'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Taxable Turnover</span>
              <p className="text-xl font-bold text-white mt-1">
                ₹{((gstSummary?.taxable_turnover_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">From issued invoices</span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Output CGST (Intra-state)</span>
              <p className="text-xl font-bold text-indigo-400 mt-1">
                ₹{((gstSummary?.output_cgst_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">Central tax liability</span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Output SGST (Intra-state)</span>
              <p className="text-xl font-bold text-indigo-400 mt-1">
                ₹{((gstSummary?.output_sgst_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">State tax liability</span>
            </Card>

            <Card className="p-4 border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-400">Output IGST (Inter-state)</span>
              <p className="text-xl font-bold text-indigo-400 mt-1">
                ₹{((gstSummary?.output_igst_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block">Integrated tax liability</span>
            </Card>
          </div>

          <Card className="p-4 border-slate-800 bg-slate-900/40">
            <h3 className="text-sm font-semibold text-white mb-2">Net GST Readiness Calculation</h3>
            <div className="divide-y divide-slate-800 text-xs">
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-300">Total Output GST Collected</span>
                <span className="font-semibold text-white">
                  ₹{((gstSummary?.total_output_gst_paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-300">Invoices Included in Calculation</span>
                <span className="font-semibold text-white">{gstSummary?.invoices_analyzed_count || 0}</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 6: Income Tax Estimator */}
      {activeTab === 'tax_estimator' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Income Tax Estimator & Comparison</h2>
              <p className="text-xs text-slate-400">
                Mathematical projection of Indian Income Tax for {selectedPeriod?.fiscal_year} comparing Old vs New Regime.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={selectedRegime === 'new_regime' ? 'primary' : 'outline'}
                size="sm"
                className="text-xs"
                onClick={() => {
                  setSelectedRegime('new_regime');
                  handleCalculateEstimate('new_regime');
                }}
              >
                New Regime (Default)
              </Button>
              <Button
                variant={selectedRegime === 'old_regime' ? 'primary' : 'outline'}
                size="sm"
                className="text-xs"
                onClick={() => {
                  setSelectedRegime('old_regime');
                  handleCalculateEstimate('old_regime');
                }}
              >
                Old Regime
              </Button>
            </div>
          </div>

          {/* Statutory Disclaimer Alert */}
          <div className="p-4 rounded-xl border border-indigo-800/40 bg-indigo-950/20 text-indigo-300 text-xs flex items-start gap-3">
            <Info size={18} className="shrink-0 mt-0.5 text-indigo-400" />
            <div>
              <p className="font-semibold text-indigo-200">Mathematical Estimation Notice</p>
              <p className="mt-1 leading-relaxed opacity-90">
                {taxEstimate?.statutory_disclaimer ||
                  'ARTHSAVORA Tax Intelligence provides purely mathematical estimations for informational planning. It does not constitute certified tax advice or formal filing.'}
              </p>
            </div>
          </div>

          {taxEstimate && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="p-5 border-slate-800 bg-slate-900/40 space-y-3">
                <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
                  Tax Computation Breakdown ({taxEstimate.regime.replace(/_/g, ' ').toUpperCase()})
                </h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gross Income (Verified FY Inflow)</span>
                    <span className="font-medium text-white">
                      ₹{(taxEstimate.gross_income_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between text-emerald-400">
                    <span>Less: Standard Deduction</span>
                    <span>-₹{(taxEstimate.standard_deduction_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-emerald-400">
                    <span>Less: Section 80C &amp; 80D Deductions</span>
                    <span>-₹{(taxEstimate.chapter_via_deductions_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="border-t border-slate-800 pt-2 flex justify-between font-semibold text-slate-200">
                    <span>Taxable Net Income</span>
                    <span>₹{(taxEstimate.taxable_income_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Slab Tax Calculated</span>
                    <span>₹{(taxEstimate.slab_tax_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  {taxEstimate.rebate_87a_paise > 0 && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Less: Section 87A Full Rebate</span>
                      <span>-₹{(taxEstimate.rebate_87a_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-slate-400">
                    <span>Add: 4% Health &amp; Education Cess</span>
                    <span>₹{(taxEstimate.health_education_cess_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="border-t border-indigo-800/40 pt-3 flex justify-between text-base font-bold text-indigo-400">
                    <span>Total Estimated Tax Liability</span>
                    <span>₹{(taxEstimate.total_estimated_tax_paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
              </Card>

              <Card className="p-5 border-slate-800 bg-slate-900/40 space-y-4">
                <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-2">
                  Key Planning Insights
                </h3>
                <div>
                  <span className="text-xs text-slate-400">Effective Tax Rate</span>
                  <p className="text-2xl font-bold text-white mt-0.5">{(taxEstimate.effective_tax_rate_percent ?? 0).toFixed(2)}%</p>
                </div>
                <div>
                  <span className="text-xs text-slate-400">Assessment Year</span>
                  <p className="text-sm font-mono text-slate-200">{taxEstimate.assessment_year || '-'}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                  <p className="font-semibold text-slate-200 mb-1">Calculation Assumptions:</p>
                  <p>{taxEstimate.assumptions_narrative || 'Standard statutory deductions applied.'}</p>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Validation Center */}
      {activeTab === 'validations' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white">Financial Validation & Quality Assurance</h2>
            <p className="text-xs text-slate-400">
              Deterministic audits verifying trial balance equality, balance sheet equilibrium, and missing documentation.
            </p>
          </div>

          <div className="space-y-3">
            {validationFindings.map((finding) => (
              <Card
                key={finding.id}
                className={`p-4 border ${
                  finding.severity === 'critical'
                    ? 'border-rose-800/50 bg-rose-950/10'
                    : 'border-amber-800/50 bg-amber-950/10'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={finding.severity === 'critical' ? 'expense' : 'warning'} className="text-[10px]">
                        {finding.rule_code}
                      </Badge>
                      <h4 className="font-semibold text-sm text-white">{finding.title}</h4>
                    </div>
                    <p className="text-xs text-slate-300">{finding.description}</p>
                    {finding.recommended_action && (
                      <p className="text-xs text-slate-400 italic">Recommendation: {finding.recommended_action}</p>
                    )}
                  </div>
                  {!finding.is_resolved ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs gap-1"
                      onClick={() => handleResolveFinding(finding.id)}
                    >
                      <Check size={12} /> Mark Resolved
                    </Button>
                  ) : (
                    <Badge variant="brand" className="text-emerald-400 border-emerald-800 text-[10px]">
                      Resolved
                    </Badge>
                  )}
                </div>
              </Card>
            ))}

            {validationFindings.length === 0 && (
              <Card className="p-8 text-center border-slate-800 bg-slate-900/40">
                <CheckCircle className="mx-auto text-emerald-400 mb-2" size={32} />
                <p className="text-sm font-semibold text-white">All Financial Audits Passed</p>
                <p className="text-xs text-slate-400 mt-1">
                  Trial balance is balanced, balance sheet equation holds, and large transactions have supporting evidence.
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Tab 8: Historical Snapshots */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white">Report Snapshots & Secure Exports</h2>
            <p className="text-xs text-slate-400">
              Immutable historical report records with formula-injection defenses (CWE-1236) and SHA-256 data checksums.
            </p>
          </div>

          <Card className="border-slate-800 bg-slate-900/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Title</th>
                    <th className="py-3 px-4">Period</th>
                    <th className="py-3 px-4">Basis</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Checksum</th>
                    <th className="py-3 px-4 text-right">Download</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {generatedReports.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-800/20">
                      <td className="py-3 px-4 font-semibold text-white">{report.title}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {report.start_date} to {report.end_date}
                      </td>
                      <td className="py-3 px-4 capitalize font-mono text-slate-300">{report.accounting_basis}</td>
                      <td className="py-3 px-4">
                        <Badge variant="neutral" className="text-[10px] capitalize">
                          {report.validation_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-[10px] text-slate-500">
                        {report.checksum ? `${report.checksum.slice(0, 8)}...` : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                          onClick={() => handleDownloadCSV(report.id, report.title)}
                        >
                          <Download size={14} /> CSV
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {generatedReports.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 text-xs">
                        No report snapshots generated yet. Generate a statement snapshot from any tab above.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* Tax Review Modal */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title="Review Transaction Tax Classification"
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Tax Category</label>
            <select
              aria-label="Tax Category"
              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-white text-xs"
              value={reviewCategory}
              onChange={(e) => setReviewCategory(e.target.value)}
            >
              <option value="section_80c">Section 80C (PPF, ELSS, EPF, Term Insurance)</option>
              <option value="section_80d">Section 80D (Health Insurance Premium)</option>
              <option value="business_expense_deductible">Business Operating Expense (Deductible)</option>
              <option value="exempt_income">Exempt Income (Agricultural / Dividend / Gift)</option>
              <option value="gst_eligible_expense">GST Input Tax Credit Eligible Expense</option>
              <option value="personal_non_deductible">Personal Discretionary (Non-deductible)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Deductible Amount (₹)</label>
            <Input
              type="number"
              value={reviewDeductible}
              onChange={(e) => setReviewDeductible(parseFloat(e.target.value) || 0)}
              placeholder="0.00"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Review Notes &amp; Statutory Justification</label>
            <Input
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="e.g. Health insurance receipt verified for FY 2026-27"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsReviewModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleConfirmReview}>
              Confirm Classification
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default FinancialReports;
