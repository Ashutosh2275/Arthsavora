import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FinancialReports } from '../FinancialReports';
import { useFinancialReportStore } from '@/store/useFinancialReportStore';

vi.mock('@/store/useFinancialReportStore');

const mockPeriods = [
  {
    period_type: 'financial_year',
    fiscal_year: 'FY 2026-27',
    quarter: null,
    start_date: '2026-04-01',
    end_date: '2027-03-31',
    label: 'Financial Year FY 2026-27 (Apr 1, 2026 - Mar 31, 2027)',
  },
  {
    period_type: 'quarterly',
    fiscal_year: 'FY 2026-27',
    quarter: 1,
    start_date: '2026-04-01',
    end_date: '2026-06-30',
    label: 'FY 2026-27 Q1 (Apr-Jun)',
  },
];

const mockIncomeStatement = {
  period: mockPeriods[0],
  basis: 'cash',
  currency: 'INR',
  total_income_paise: 25000000,
  total_expense_paise: 10000000,
  net_surplus_deficit_paise: 15000000,
  income_lines: [
    {
      account_code: 'REV-001',
      account_name: 'Professional Consulting',
      account_type: 'revenue',
      balance_paise: 25000000,
      percentage_of_total: 100.0,
    },
  ],
  expense_lines: [
    {
      account_code: 'EXP-001',
      account_name: 'Cloud Hosting & Infrastructure',
      account_type: 'expense',
      balance_paise: 10000000,
      percentage_of_total: 100.0,
    },
  ],
  data_quality_warnings: [],
};

const mockBalanceSheet = {
  as_of_date: '2027-03-31',
  currency: 'INR',
  total_assets_paise: 50000000,
  total_liabilities_paise: 20000000,
  total_equity_paise: 30000000,
  is_balanced: true,
  discrepancy_paise: 0,
  asset_lines: [],
  liability_lines: [],
  equity_lines: [],
  validation_notes: ['Assets equal Liabilities plus Equity perfectly.'],
};

const mockGSTSummary = {
  reporting_period: mockPeriods[0],
  currency: 'INR',
  taxable_turnover_paise: 100000000,
  output_cgst_paise: 9000000,
  output_sgst_paise: 9000000,
  output_igst_paise: 0,
  total_tax_liability_paise: 18000000,
  invoices_analyzed_count: 12,
  rate_breakdown: [
    {
      rate_percent: 18.0,
      taxable_turnover_paise: 100000000,
      cgst_paise: 9000000,
      sgst_paise: 9000000,
      igst_paise: 0,
      total_tax_paise: 18000000,
    },
  ],
  b2b_invoices_count: 12,
  b2c_invoices_count: 0,
  disclaimer: 'This GST report provides structured accounting preparation data and does not constitute a certified GSTR-1 or GSTR-3B tax filing.',
};

const mockTaxEstimate = {
  financial_year: 'FY 2026-27',
  regime: 'new_regime',
  gross_income_paise: 200000000,
  standard_deduction_paise: 7500000,
  chapter_via_deductions_paise: 0,
  taxable_income_paise: 192500000,
  slab_tax_paise: 22750000,
  rebate_87a_paise: 0,
  health_education_cess_paise: 910000,
  total_estimated_tax_paise: 23660000,
  effective_tax_rate_percent: 11.83,
  assessment_year: 'AY 2027-28',
  assumptions_narrative: 'Standard statutory deductions applied under Section 115BAC.',
  statutory_disclaimer: 'Tax estimation is purely mathematical for planning purposes.',
};

describe('FinancialReports Page Component', () => {
  const mockFetchPeriods = vi.fn();
  const mockFetchIncomeStatement = vi.fn();
  const mockFetchCashFlowStatement = vi.fn();
  const mockFetchBalanceSheet = vi.fn();
  const mockFetchTrialBalance = vi.fn();
  const mockFetchTaxClassifications = vi.fn();
  const mockFetchGSTSummary = vi.fn();
  const mockFetchTaxEstimate = vi.fn();
  const mockFetchValidations = vi.fn();
  const mockFetchReportHistory = vi.fn();
  const mockSelectPeriod = vi.fn();
  const mockSetAccountingBasis = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useFinancialReportStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      periods: mockPeriods,
      selectedPeriod: mockPeriods[0],
      accountingBasis: 'cash',
      incomeStatement: mockIncomeStatement,
      cashFlowStatement: null,
      balanceSheet: mockBalanceSheet,
      trialBalance: null,
      taxClassifications: [],
      gstSummary: mockGSTSummary,
      taxEstimate: mockTaxEstimate,
      validationFindings: [],
      generatedReports: [],
      isLoading: false,
      error: null,
      fetchPeriods: mockFetchPeriods,
      fetchIncomeStatement: mockFetchIncomeStatement,
      fetchCashFlowStatement: mockFetchCashFlowStatement,
      fetchBalanceSheet: mockFetchBalanceSheet,
      fetchTrialBalance: mockFetchTrialBalance,
      fetchTaxClassifications: mockFetchTaxClassifications,
      fetchGSTSummary: mockFetchGSTSummary,
      fetchTaxEstimate: mockFetchTaxEstimate,
      fetchValidations: mockFetchValidations,
      fetchReportHistory: mockFetchReportHistory,
      selectPeriod: mockSelectPeriod,
      setAccountingBasis: mockSetAccountingBasis,
      generateReportSnapshot: vi.fn(),
      downloadReportCSV: vi.fn(),
      suggestTaxClassifications: vi.fn(),
      reviewTaxClassification: vi.fn(),
      createTaxEstimate: vi.fn(),
      resolveValidation: vi.fn(),
    });
  });

  it('renders header and calls initial data loaders', () => {
    render(<FinancialReports />);
    expect(screen.getByRole('heading', { name: /Financial Reports & Tax Intelligence/i })).toBeInTheDocument();
    expect(screen.getByText(/Verified financial statements, Indian Financial Year reporting/i)).toBeInTheDocument();
    expect(mockFetchPeriods).toHaveBeenCalled();
  });

  it('displays the Income Statement metrics and line items', () => {
    render(<FinancialReports />);
    expect(screen.getByText('Income and Expense Statement')).toBeInTheDocument();
    expect(screen.getByText('Professional Consulting')).toBeInTheDocument();
    expect(screen.getByText('Cloud Hosting & Infrastructure')).toBeInTheDocument();
  });

  it('switches between tabs cleanly to Balance Sheet and verifies equation indicator', () => {
    render(<FinancialReports />);
    const bsTab = screen.getByRole('button', { name: /Balance Sheet & Trial Balance/i });
    fireEvent.click(bsTab);
    expect(mockFetchBalanceSheet).toHaveBeenCalled();
    expect(screen.getByText(/Balance Sheet Equation Balanced \(Assets = Liabilities \+ Equity\)/i)).toBeInTheDocument();
  });

  it('switches to GST Readiness tab and renders GST turnover breakdown', () => {
    render(<FinancialReports />);
    const gstTab = screen.getByRole('button', { name: /GST Readiness/i });
    fireEvent.click(gstTab);
    expect(mockFetchGSTSummary).toHaveBeenCalled();
    expect(screen.getByText('Taxable Turnover')).toBeInTheDocument();
    expect(screen.getByText(/Output CGST \(Intra-state\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Output SGST \(Intra-state\)/i)).toBeInTheDocument();
  });

  it('switches to Income Tax Estimator tab and renders computation breakdown', () => {
    render(<FinancialReports />);
    const taxTab = screen.getByRole('button', { name: /Income Tax Estimator/i });
    fireEvent.click(taxTab);
    expect(mockFetchTaxEstimate).toHaveBeenCalled();
    expect(screen.getByText(/Tax Computation Breakdown/i)).toBeInTheDocument();
    expect(screen.getByText(/Mathematical Estimation Notice/i)).toBeInTheDocument();
    expect(screen.getByText('11.83%')).toBeInTheDocument();
  });

  it('switches to Validation Center tab and verifies data quality section', () => {
    render(<FinancialReports />);
    const auditTab = screen.getByRole('button', { name: /Validation Center/i });
    fireEvent.click(auditTab);
    expect(mockFetchValidations).toHaveBeenCalled();
    expect(screen.getByText('All Financial Audits Passed')).toBeInTheDocument();
    expect(screen.getByText(/Trial balance is balanced, balance sheet equation holds/i)).toBeInTheDocument();
  });
});
