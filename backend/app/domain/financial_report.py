"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance Readiness Domain Model
Pure, immutable domain entities, value objects, enums, date boundary math, and tax calculation rules.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class ReportType(str, Enum):
    INCOME_AND_EXPENSE = "income_and_expense"
    CASH_FLOW = "cash_flow"
    BALANCE_SHEET = "balance_sheet"
    TRIAL_BALANCE = "trial_balance"
    GENERAL_LEDGER = "general_ledger"
    ACCOUNT_STATEMENT = "account_statement"
    PERSONAL_SUMMARY = "personal_summary"
    FAMILY_SUMMARY = "family_summary"
    BUSINESS_SUMMARY = "business_summary"
    TAX_SUMMARY = "tax_summary"
    GST_REPORT = "gst_report"
    TAX_DOCUMENT_INDEX = "tax_document_index"


class AccountingBasis(str, Enum):
    CASH = "cash"
    ACCRUAL = "accrual"


class PeriodType(str, Enum):
    FINANCIAL_YEAR = "financial_year"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    CUSTOM = "custom"


class TaxReviewStatus(str, Enum):
    UNCLASSIFIED = "unclassified"
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REVIEWED = "reviewed"
    EXCLUDED = "excluded"


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ExportFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"


class TaxJurisdiction(str, Enum):
    INDIA = "IN"
    UNITED_STATES = "US"
    UNITED_KINGDOM = "UK"
    GLOBAL = "GLOBAL"


class TaxpayerCategory(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    HUF = "huf"
    LLP = "llp"
    COMPANY = "company"


class TaxRegime(str, Enum):
    NEW_REGIME = "new_regime"
    OLD_REGIME = "old_regime"


# -----------------------------------------------------------------------------
# Value Objects
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ReportingPeriodVO:
    """Encapsulates a validated date range for financial reporting."""
    period_type: str
    start_date: date
    end_date: date
    label: str
    fiscal_year: Optional[str] = None
    quarter: Optional[int] = None

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})")


@dataclass(frozen=True)
class StatementLineVO:
    """Individual line item in a financial report."""
    account_code: str
    account_name: str
    account_type: str  # asset, liability, equity, revenue, expense
    sub_type: Optional[str]
    balance_paise: int
    display_amount: Decimal
    currency: str = "INR"
    percentage_of_total: Optional[Decimal] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class IncomeExpenseStatementVO:
    """Income and Expense report for a specified period and accounting basis."""
    reporting_period: ReportingPeriodVO
    accounting_basis: AccountingBasis
    currency: str
    operating_income_paise: int
    other_income_paise: int
    total_income_paise: int
    direct_expenses_paise: int
    operating_expenses_paise: int
    financial_expenses_paise: int
    total_expenses_paise: int
    net_surplus_deficit_paise: int
    income_lines: List[StatementLineVO] = field(default_factory=list)
    expense_lines: List[StatementLineVO] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CashFlowStatementVO:
    """Statement of Cash Flows analyzing liquidity movements."""
    reporting_period: ReportingPeriodVO
    currency: str
    operating_inflows_paise: int
    operating_outflows_paise: int
    net_operating_cash_flow_paise: int
    investing_inflows_paise: int
    investing_outflows_paise: int
    net_investing_cash_flow_paise: int
    financing_inflows_paise: int
    financing_outflows_paise: int
    net_financing_cash_flow_paise: int
    net_cash_movement_paise: int
    opening_cash_balance_paise: int
    closing_cash_balance_paise: int
    inflow_lines: List[StatementLineVO] = field(default_factory=list)
    outflow_lines: List[StatementLineVO] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BalanceSheetVO:
    """Point-in-time Balance Sheet evaluating Assets = Liabilities + Equity."""
    as_of_date: date
    currency: str
    total_assets_paise: int
    total_liabilities_paise: int
    total_equity_paise: int
    is_balanced: bool
    discrepancy_paise: int
    asset_lines: List[StatementLineVO] = field(default_factory=list)
    liability_lines: List[StatementLineVO] = field(default_factory=list)
    equity_lines: List[StatementLineVO] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TrialBalanceReportVO:
    """Complete trial balance with debit/credit balance equality check."""
    as_of_date: date
    currency: str
    total_debits_paise: int
    total_credits_paise: int
    is_balanced: bool
    discrepancy_paise: int
    lines: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TaxClassificationVO:
    """Classified tax metadata associated with a transaction."""
    transaction_id: str
    tax_category: str
    tax_category_code: str
    tax_year: str
    review_status: TaxReviewStatus
    confidence_score: float
    deductible_amount_paise: int
    gst_component: Optional[str] = None  # CGST, SGST, IGST
    hsn_sac_code: Optional[str] = None
    tax_rate_percent: Optional[Decimal] = None
    notes: Optional[str] = None
    rule_code: Optional[str] = None
    evidence_document_id: Optional[str] = None


@dataclass(frozen=True)
class GSTReportSummaryVO:
    """Summary of GST outputs, inputs, and taxable turnover for a period."""
    period_label: str
    financial_year: str
    gstin: Optional[str]
    taxable_sales_paise: int
    exempt_sales_paise: int
    non_taxable_sales_paise: int
    total_turnover_paise: int
    output_cgst_paise: int
    output_sgst_paise: int
    output_igst_paise: int
    total_output_tax_paise: int
    input_tax_recorded_paise: int
    estimated_net_tax_liability_paise: int
    invoices_analyzed_count: int
    data_disclaimer: str = (
        "Informational business record report only. ARTHSAVORA is not an authorized GST Suvidha Provider (GSP), "
        "and this document is not a certified tax filing or return."
    )


@dataclass(frozen=True)
class IncomeTaxEstimateVO:
    """Non-certified illustrative Indian Income Tax estimate."""
    financial_year: str
    assessment_year: str
    taxpayer_category: str
    regime: str
    gross_total_income_paise: int
    standard_deduction_paise: int
    chapter_vi_a_deductions_paise: int
    taxable_income_paise: int
    base_tax_paise: int
    surcharge_paise: int
    cess_paise: int
    total_estimated_tax_paise: int
    effective_tax_rate_percent: Decimal
    assumptions_narrative: str
    missing_data_warnings: List[str] = field(default_factory=list)
    legal_disclaimer: str = (
        "Illustrative tax estimate only based on standard mathematical slabs. ARTHSAVORA is not a chartered "
        "accountant or licensed tax preparer. Do not use for official tax filings without professional review."
    )


@dataclass(frozen=True)
class ReportValidationFindingVO:
    """Discrepancy or data quality finding generated by validation engine."""
    code: str
    severity: ValidationSeverity
    title: str
    description: str
    affected_entity_id: Optional[str] = None
    recommended_action: Optional[str] = None


# -----------------------------------------------------------------------------
# Pure Functions & Calculations
# -----------------------------------------------------------------------------

def calculate_indian_financial_year(reference_date: date) -> str:
    """
    Computes Indian Financial Year (April 1 - March 31) for a given date.
    Example: 2026-05-15 -> 'FY 2026-27', 2026-02-10 -> 'FY 2025-26'
    """
    if reference_date.month >= 4:
        start_y = reference_date.year
        end_y = (reference_date.year + 1) % 100
        return f"FY {start_y}-{end_y:02d}"
    else:
        start_y = reference_date.year - 1
        end_y = reference_date.year % 100
        return f"FY {start_y}-{end_y:02d}"


def calculate_financial_year_bounds(fiscal_year_str: str) -> Tuple[date, date]:
    """
    Parses 'YYYY-YYYY', 'YYYY-YY', 'FY YYYY-YY', or 'FY YYYY-YYYY' into start and end calendar dates under April-March rule.
    Example: 'FY 2026-27' -> (date(2026, 4, 1), date(2027, 3, 31))
    """
    cleaned = fiscal_year_str.strip().upper()
    if cleaned.startswith("FY"):
        cleaned = cleaned[2:].strip()
    match = re.match(r"^(\d{4})\s*[-/]\s*(\d{2,4})$", cleaned)
    if not match:
        raise ValueError(
            f"Invalid fiscal year format: '{fiscal_year_str}'. Expected 'FY YYYY-YY' or 'YYYY-YYYY' (e.g. 'FY 2026-27' or '2026-2027')."
        )
    start_year = int(match.group(1))
    end_raw = match.group(2)
    if len(end_raw) == 2:
        end_year = int(str(start_year)[:2] + end_raw)
    else:
        end_year = int(end_raw)

    if end_year != start_year + 1:
        raise ValueError(f"Fiscal year span must be exactly 1 year. Got {start_year} to {end_year}.")
    return date(start_year, 4, 1), date(end_year, 3, 31)


def calculate_quarter_bounds(fiscal_year_str: str, quarter: int) -> Tuple[date, date, str]:
    """
    Returns (start_date, end_date, label) for an Indian fiscal year quarter:
    Q1: Apr 1 - Jun 30
    Q2: Jul 1 - Sep 30
    Q3: Oct 1 - Dec 31
    Q4: Jan 1 - Mar 31 (following year)
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Quarter must be 1, 2, 3, or 4. Got {quarter}.")
    fy_start, fy_end = calculate_financial_year_bounds(fiscal_year_str)
    start_year = fy_start.year
    end_year = fy_end.year

    if quarter == 1:
        return date(start_year, 4, 1), date(start_year, 6, 30), f"Q1 FY {fiscal_year_str} (Apr - Jun {start_year})"
    elif quarter == 2:
        return date(start_year, 7, 1), date(start_year, 9, 30), f"Q2 FY {fiscal_year_str} (Jul - Sep {start_year})"
    elif quarter == 3:
        return date(start_year, 10, 1), date(start_year, 12, 31), f"Q3 FY {fiscal_year_str} (Oct - Dec {start_year})"
    else:
        return date(end_year, 1, 1), date(end_year, 3, 31), f"Q4 FY {fiscal_year_str} (Jan - Mar {end_year})"


def sanitize_csv_cell(value: Any) -> str:
    """
    Prevents CSV Formula Injection (CWE-1236).
    If a cell starts with '=', '+', '-', or '@', prepends a single quote (').
    """
    if value is None:
        return ""
    text_val = str(value)
    if text_val and text_val[0] in ("=", "+", "-", "@"):
        return f"'{text_val}"
    return text_val


def validate_balance_sheet_equation(
    assets_paise: int,
    liabilities_paise: int,
    equity_paise: int,
) -> Tuple[bool, int, str]:
    """
    Enforces Fundamental Accounting Equation:
    Assets = Liabilities + Equity
    Returns (is_balanced, discrepancy_paise, explanation).
    """
    r_side = liabilities_paise + equity_paise
    diff = assets_paise - r_side
    if diff == 0:
        return True, 0, "Perfect Balance: Total Assets match Total Liabilities + Equity."
    else:
        diff_abs = abs(diff)
        diff_fmt = f"₹{diff_abs / 100:,.2f}"
        if diff > 0:
            return False, diff, f"Unbalanced: Assets exceed Liabilities + Equity by {diff_fmt}."
        else:
            return False, diff, f"Unbalanced: Liabilities + Equity exceed Assets by {diff_fmt}."


def estimate_indian_income_tax(
    gross_income_paise: int,
    deductions_paise: int = 0,
    regime: str = TaxRegime.NEW_REGIME.value,
    fy: str = "2026-2027",
) -> IncomeTaxEstimateVO:
    """
    Computes conservative Indian Income Tax estimate for Individuals under Indian Finance Act.
    Supports New Regime (Section 115BAC default with 75k standard deduction)
    and Old Regime (with Section 80C, 80D, standard deduction).
    All calculation is in exact paise integer arithmetic.
    """
    gross_dec = Decimal(gross_income_paise) / Decimal(100)
    
    std_ded_paise = 7500000 if regime == TaxRegime.NEW_REGIME.value else 5000000
    applied_deductions_paise = std_ded_paise

    if regime == TaxRegime.OLD_REGIME.value:
        applied_deductions_paise += deductions_paise

    taxable_paise = max(0, gross_income_paise - applied_deductions_paise)
    taxable_rupees = taxable_paise // 100

    base_tax_rupees = 0

    if regime == TaxRegime.NEW_REGIME.value:
        # Finance Act 2024 / 2025 Slabs (New Regime):
        # 0 to 3L: Nil
        # 3L to 7L: 5%
        # 7L to 10L: 10%
        # 10L to 12L: 15%
        # 12L to 15L: 20%
        # Above 15L: 30%
        # Rebate u/s 87A: If taxable income <= 7L, tax is zero
        if taxable_rupees <= 700000:
            base_tax_rupees = 0
        else:
            if taxable_rupees > 1500000:
                base_tax_rupees += int((taxable_rupees - 1500000) * 0.30)
                rem = 1500000
            else:
                rem = taxable_rupees

            if rem > 1200000:
                base_tax_rupees += int((rem - 1200000) * 0.20)
                rem = 1200000
            if rem > 1000000:
                base_tax_rupees += int((rem - 1000000) * 0.15)
                rem = 1000000
            if rem > 700000:
                base_tax_rupees += int((rem - 700000) * 0.10)
                rem = 700000
            if rem > 300000:
                base_tax_rupees += int((rem - 300000) * 0.05)

    else:
        # Old Regime Slabs:
        # 0 to 2.5L: Nil
        # 2.5L to 5L: 5%
        # 5L to 10L: 20%
        # Above 10L: 30%
        # Rebate u/s 87A: If taxable income <= 5L, tax is zero
        if taxable_rupees <= 500000:
            base_tax_rupees = 0
        else:
            if taxable_rupees > 1000000:
                base_tax_rupees += int((taxable_rupees - 1000000) * 0.30)
                rem = 1000000
            else:
                rem = taxable_rupees

            if rem > 500000:
                base_tax_rupees += int((rem - 500000) * 0.20)
                rem = 500000
            if rem > 250000:
                base_tax_rupees += int((rem - 250000) * 0.05)

    # 4% Health & Education Cess
    cess_rupees = int(round(base_tax_rupees * 0.04))
    total_tax_rupees = base_tax_rupees + cess_rupees
    total_tax_paise = total_tax_rupees * 100

    eff_rate = Decimal(0)
    if gross_income_paise > 0:
        eff_rate = Decimal(round((total_tax_paise / gross_income_paise) * 100, 2))

    # Assessment year is FY + 1
    fy_start, _ = calculate_financial_year_bounds(fy)
    ay = f"{fy_start.year + 1}-{fy_start.year + 2}"

    return IncomeTaxEstimateVO(
        financial_year=fy,
        assessment_year=ay,
        taxpayer_category=TaxpayerCategory.INDIVIDUAL.value,
        regime=regime,
        gross_total_income_paise=gross_income_paise,
        standard_deduction_paise=std_ded_paise,
        chapter_vi_a_deductions_paise=deductions_paise if regime == TaxRegime.OLD_REGIME.value else 0,
        taxable_income_paise=taxable_paise,
        base_tax_paise=base_tax_rupees * 100,
        surcharge_paise=0,
        cess_paise=cess_rupees * 100,
        total_estimated_tax_paise=total_tax_paise,
        effective_tax_rate_percent=eff_rate,
        assumptions_narrative=(
            f"Calculated under {regime.replace('_', ' ').title()} slabs for FY {fy}. "
            f"Includes standard deduction of ₹{std_ded_paise / 100:,.0f} and 4% Health & Education Cess."
        ),
        missing_data_warnings=[],
    )
