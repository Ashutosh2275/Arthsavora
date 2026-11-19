"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance Schemas
Defines request and response serialization contracts for financial statements,
tax classifications, GST summaries, income tax estimates, and report validations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Reporting Period & Statement Line Schemas
# ---------------------------------------------------------------------------
class ReportingPeriodResponse(BaseModel):
    period_type: str
    fiscal_year: str
    quarter: Optional[int] = None
    start_date: date
    end_date: date
    label: str

    class Config:
        from_attributes = True


class StatementLineResponse(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    sub_type: Optional[str] = None
    balance_paise: int
    display_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    percentage_of_total: Optional[float] = 0.0
    notes: Optional[str] = None

    class Config:
        from_attributes = True
        extra = "ignore"


# ---------------------------------------------------------------------------
# 2. Financial Statements Schemas
# ---------------------------------------------------------------------------
class IncomeExpenseStatementResponse(BaseModel):
    period: ReportingPeriodResponse
    basis: str
    currency: str
    total_income_paise: int
    total_expense_paise: int
    net_surplus_deficit_paise: int
    income_lines: List[StatementLineResponse] = Field(default_factory=list)
    expense_lines: List[StatementLineResponse] = Field(default_factory=list)
    data_quality_warnings: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CashFlowStatementResponse(BaseModel):
    period: ReportingPeriodResponse
    currency: str
    operating_inflows_paise: int
    operating_outflows_paise: int
    net_operating_cash_flow_paise: int
    net_investing_cash_flow_paise: int
    net_financing_cash_flow_paise: int
    net_cash_change_paise: int
    opening_cash_balance_paise: int
    closing_cash_balance_paise: int
    data_quality_warnings: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BalanceSheetResponse(BaseModel):
    as_of_date: date
    currency: str
    total_assets_paise: int
    total_liabilities_paise: int
    total_equity_paise: int
    is_balanced: bool
    discrepancy_paise: int
    asset_lines: List[StatementLineResponse] = Field(default_factory=list)
    liability_lines: List[StatementLineResponse] = Field(default_factory=list)
    equity_lines: List[StatementLineResponse] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TrialBalanceResponse(BaseModel):
    as_of_date: date
    currency: str
    total_debits_paise: int
    total_credits_paise: int
    is_balanced: bool
    discrepancy_paise: int
    lines: List[StatementLineResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 3. Report Generation & History Schemas
# ---------------------------------------------------------------------------
class GenerateReportRequest(BaseModel):
    report_type: str = Field(..., description="income_statement, cash_flow, balance_sheet, trial_balance")
    period_type: str = Field(default="financial_year", description="financial_year, quarter, month, custom")
    fiscal_year: Optional[str] = Field(default=None, description="e.g. FY 2026-27")
    quarter: Optional[int] = Field(default=None, ge=1, le=4)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    as_of_date: Optional[date] = None
    basis: str = Field(default="cash", description="cash or accrual")
    format: str = Field(default="json", description="json or csv")


class GeneratedReportResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    report_type: str
    title: str
    accounting_basis: str
    period_type: str
    start_date: date
    end_date: date
    validation_status: str
    file_format: Optional[str] = None
    parameters_json: Dict[str, Any] = Field(default_factory=dict)
    report_data_json: Dict[str, Any] = Field(default_factory=dict)
    checksum: Optional[str] = None
    generated_by_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 4. Tax Classification Schemas
# ---------------------------------------------------------------------------
class TaxClassificationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    transaction_id: UUID
    tax_year: str
    tax_category: str
    tax_category_code: Optional[str] = None
    review_status: str
    rule_code: Optional[str] = None
    rule_version: Optional[str] = None
    taxable_amount_paise: int
    deductible_amount_paise: int
    gst_rate_percent: Optional[float] = None
    gst_amount_paise: Optional[int] = None
    evidence_document_id: Optional[UUID] = None
    user_notes: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewTaxClassificationRequest(BaseModel):
    tax_category: str = Field(..., description="tax category e.g. section_80c, section_80d, business_expense_deductible")
    review_status: str = Field(default="confirmed", description="confirmed, reviewed, rejected")
    notes: Optional[str] = None
    deductible_amount_paise: Optional[int] = None
    evidence_document_id: Optional[UUID] = None


class SuggestTaxClassificationsRequest(BaseModel):
    tax_year: Optional[str] = Field(default=None, description="e.g. FY 2026-27")


# ---------------------------------------------------------------------------
# 5. GST Reporting Schemas
# ---------------------------------------------------------------------------
class GSTReportSummaryResponse(BaseModel):
    period: ReportingPeriodResponse
    currency: str
    taxable_turnover_paise: int
    exempt_turnover_paise: int
    total_turnover_paise: int
    output_cgst_paise: int
    output_sgst_paise: int
    output_igst_paise: int
    total_output_gst_paise: int
    estimated_input_tax_credit_paise: int
    estimated_net_gst_payable_paise: int
    invoices_analyzed_count: int
    disclaimer: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 6. Income Tax Estimation Schemas
# ---------------------------------------------------------------------------
class TaxEstimateResponse(BaseModel):
    financial_year: str
    assessment_year: str
    taxpayer_category: str
    regime: str
    gross_income_paise: int
    standard_deduction_paise: int
    chapter_via_deductions_paise: int
    taxable_income_paise: int
    slab_tax_paise: int
    rebate_87a_paise: int
    health_education_cess_paise: int
    total_estimated_tax_paise: int
    effective_tax_rate_percent: float
    assumptions_narrative: str
    missing_data_warnings: List[str] = Field(default_factory=list)
    statutory_disclaimer: str

    class Config:
        from_attributes = True


class CreateTaxEstimateRequest(BaseModel):
    financial_year: Optional[str] = Field(default=None, description="e.g. FY 2026-27")
    regime: str = Field(default="new_regime", description="new_regime or old_regime")


# ---------------------------------------------------------------------------
# 7. Report Validation Finding Schemas
# ---------------------------------------------------------------------------
class ReportValidationFindingResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    report_type: str
    period_start: date
    period_end: date
    rule_code: str
    severity: str
    title: str
    description: str
    recommended_action: Optional[str] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResolveValidationFindingRequest(BaseModel):
    notes: Optional[str] = None
