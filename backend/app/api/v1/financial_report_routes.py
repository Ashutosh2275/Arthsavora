"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance API Endpoints
REST endpoints for financial statements, Indian financial year periods, tax classification,
GST readiness summaries, income tax calculations, report validations, and secure CSV exports.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import io
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_permission
from app.core.exceptions import NotFoundException, ValidationException
from app.core.permissions import Permission, WorkspaceContext
from app.domain.financial_report import (
    AccountingBasis,
    PeriodType,
    ReportType,
    TaxRegime,
    TaxReviewStatus,
    calculate_indian_financial_year,
    sanitize_csv_cell,
)
from app.infrastructure.database.models.financial_report import (
    GeneratedReport,
    ReportValidationFinding,
    TaxClassificationRecord,
)
from app.infrastructure.database.session import get_db_session
from app.schemas.financial_report_schema import (
    BalanceSheetResponse,
    CashFlowStatementResponse,
    CreateTaxEstimateRequest,
    GenerateReportRequest,
    GeneratedReportResponse,
    GSTReportSummaryResponse,
    IncomeExpenseStatementResponse,
    ReportingPeriodResponse,
    ReportValidationFindingResponse,
    ResolveValidationFindingRequest,
    ReviewTaxClassificationRequest,
    StatementLineResponse,
    SuggestTaxClassificationsRequest,
    TaxClassificationResponse,
    TaxEstimateResponse,
    TrialBalanceResponse,
)
from app.services.financial_reporting_service import FinancialReportingService

router = APIRouter(tags=["Financial Reporting & Tax Intelligence"])


def _to_json_safe(obj: Any) -> Any:
    """Recursively converts Decimals and date/datetime objects to JSON-serializable types."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return _to_json_safe(obj.__dict__)
    return obj


# ---------------------------------------------------------------------------
# 1. Reporting Periods & Period Discovery
# ---------------------------------------------------------------------------
@router.get(
    "/reports/periods",
    response_model=List[ReportingPeriodResponse],
    summary="Get available reporting periods for financial statements",
)
async def get_reporting_periods(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    today = date.today()
    current_fy = calculate_indian_financial_year(today)

    periods: List[ReportingPeriodResponse] = []

    # Current Financial Year
    fy_period = service.resolve_reporting_period(
        period_type=PeriodType.FINANCIAL_YEAR.value,
        fiscal_year=current_fy,
    )
    periods.append(
        ReportingPeriodResponse(
            period_type=fy_period.period_type,
            fiscal_year=fy_period.fiscal_year,
            quarter=fy_period.quarter,
            start_date=fy_period.start_date,
            end_date=fy_period.end_date,
            label=fy_period.label,
        )
    )

    # 4 Quarters for Current FY
    for q in [1, 2, 3, 4]:
        q_period = service.resolve_reporting_period(
            period_type=PeriodType.QUARTERLY.value,
            fiscal_year=current_fy,
            quarter=q,
        )
        periods.append(
            ReportingPeriodResponse(
                period_type=q_period.period_type,
                fiscal_year=q_period.fiscal_year,
                quarter=q_period.quarter,
                start_date=q_period.start_date,
                end_date=q_period.end_date,
                label=q_period.label,
            )
        )

    return periods


# ---------------------------------------------------------------------------
# 2. Live Statements Query
# ---------------------------------------------------------------------------
@router.get(
    "/reports/income-statement",
    response_model=IncomeExpenseStatementResponse,
    summary="Get live Income & Expense statement",
)
async def get_income_statement(
    period_type: str = Query(PeriodType.FINANCIAL_YEAR.value),
    fiscal_year: Optional[str] = Query(None),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    basis: str = Query(AccountingBasis.CASH.value),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    period = service.resolve_reporting_period(
        period_type=period_type,
        fiscal_year=fiscal_year,
        quarter=quarter,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = await service.generate_income_and_expense_statement(
        workspace_id=context.workspace_id,
        period=period,
        basis=basis,
    )

    return IncomeExpenseStatementResponse(
        period=ReportingPeriodResponse(
            period_type=stmt.reporting_period.period_type,
            fiscal_year=stmt.reporting_period.fiscal_year,
            quarter=stmt.reporting_period.quarter,
            start_date=stmt.reporting_period.start_date,
            end_date=stmt.reporting_period.end_date,
            label=stmt.reporting_period.label,
        ),
        basis=stmt.accounting_basis.value if hasattr(stmt.accounting_basis, 'value') else str(stmt.accounting_basis),
        currency=stmt.currency,
        total_income_paise=stmt.total_income_paise,
        total_expense_paise=stmt.total_expenses_paise,
        net_surplus_deficit_paise=stmt.net_surplus_deficit_paise,
        income_lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.income_lines
        ],
        expense_lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.expense_lines
        ],
        data_quality_warnings=stmt.data_quality_warnings,
    )


@router.get(
    "/reports/cash-flow",
    response_model=CashFlowStatementResponse,
    summary="Get live Cash Flow statement",
)
async def get_cash_flow_statement(
    period_type: str = Query(PeriodType.FINANCIAL_YEAR.value),
    fiscal_year: Optional[str] = Query(None),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    period = service.resolve_reporting_period(
        period_type=period_type,
        fiscal_year=fiscal_year,
        quarter=quarter,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = await service.generate_cash_flow_statement(
        workspace_id=context.workspace_id,
        period=period,
    )

    return CashFlowStatementResponse(
        period=ReportingPeriodResponse(
            period_type=stmt.period.period_type,
            fiscal_year=stmt.period.fiscal_year,
            quarter=stmt.period.quarter,
            start_date=stmt.period.start_date,
            end_date=stmt.period.end_date,
            label=stmt.period.label,
        ),
        currency=stmt.currency,
        operating_inflows_paise=stmt.operating_inflows_paise,
        operating_outflows_paise=stmt.operating_outflows_paise,
        net_operating_cash_flow_paise=stmt.net_operating_cash_flow_paise,
        net_investing_cash_flow_paise=stmt.net_investing_cash_flow_paise,
        net_financing_cash_flow_paise=stmt.net_financing_cash_flow_paise,
        net_cash_change_paise=stmt.net_cash_change_paise,
        opening_cash_balance_paise=stmt.opening_cash_balance_paise,
        closing_cash_balance_paise=stmt.closing_cash_balance_paise,
        data_quality_warnings=stmt.data_quality_warnings,
    )


@router.get(
    "/reports/balance-sheet",
    response_model=BalanceSheetResponse,
    summary="Get live Balance Sheet report",
)
async def get_balance_sheet(
    as_of_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    target_date = as_of_date or date.today()
    stmt = await service.generate_balance_sheet(
        workspace_id=context.workspace_id,
        as_of_date=target_date,
    )

    return BalanceSheetResponse(
        as_of_date=stmt.as_of_date,
        currency=stmt.currency,
        total_assets_paise=stmt.total_assets_paise,
        total_liabilities_paise=stmt.total_liabilities_paise,
        total_equity_paise=stmt.total_equity_paise,
        is_balanced=stmt.is_balanced,
        discrepancy_paise=stmt.discrepancy_paise,
        asset_lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.asset_lines
        ],
        liability_lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.liability_lines
        ],
        equity_lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.equity_lines
        ],
        validation_notes=stmt.validation_notes,
    )


@router.get(
    "/reports/trial-balance",
    response_model=TrialBalanceResponse,
    summary="Get live Trial Balance report",
)
async def get_trial_balance(
    as_of_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    target_date = as_of_date or date.today()
    stmt = await service.generate_trial_balance(
        workspace_id=context.workspace_id,
        as_of_date=target_date,
    )

    return TrialBalanceResponse(
        as_of_date=stmt.as_of_date,
        currency=stmt.currency,
        total_debits_paise=stmt.total_debits_paise,
        total_credits_paise=stmt.total_credits_paise,
        is_balanced=stmt.is_balanced,
        discrepancy_paise=stmt.discrepancy_paise,
        lines=[
            StatementLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                account_type=line.account_type,
                sub_type=line.sub_type,
                balance_paise=line.balance_paise,
                percentage_of_total=line.percentage_of_total,
            )
            for line in stmt.lines
        ],
    )


# ---------------------------------------------------------------------------
# 3. Report Snapshot Generation & History
# ---------------------------------------------------------------------------
@router.post(
    "/reports/generate",
    response_model=GeneratedReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist an immutable financial report snapshot",
)
async def generate_report_snapshot(
    payload: GenerateReportRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.GENERATE_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    period = service.resolve_reporting_period(
        period_type=payload.period_type,
        fiscal_year=payload.fiscal_year,
        quarter=payload.quarter,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    report_type = payload.report_type.lower()
    report_data_json: Dict[str, Any] = {}
    validation_status = "passed"
    title = f"{report_type.replace('_', ' ').title()} - {period.label}"

    if report_type in ["income_statement", "income_expense"]:
        stmt = await service.generate_income_and_expense_statement(
            workspace_id=context.workspace_id,
            period=period,
            basis=payload.basis,
        )
        report_data_json = {
            "period": {
                "period_type": period.period_type,
                "fiscal_year": period.fiscal_year,
                "quarter": period.quarter,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "label": period.label,
            },
            "basis": stmt.accounting_basis.value if hasattr(stmt.accounting_basis, 'value') else str(stmt.accounting_basis),
            "currency": stmt.currency,
            "total_income_paise": stmt.total_income_paise,
            "total_expense_paise": stmt.total_expenses_paise,
            "net_surplus_deficit_paise": stmt.net_surplus_deficit_paise,
            "income_lines": [line.__dict__ for line in stmt.income_lines],
            "expense_lines": [line.__dict__ for line in stmt.expense_lines],
            "data_quality_warnings": stmt.data_quality_warnings,
        }
    elif report_type in ["cash_flow", "cash_flow_statement"]:
        stmt = await service.generate_cash_flow_statement(
            workspace_id=context.workspace_id,
            period=period,
        )
        report_data_json = {
            "period": {
                "period_type": period.period_type,
                "fiscal_year": period.fiscal_year,
                "quarter": period.quarter,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "label": period.label,
            },
            "currency": stmt.currency,
            "operating_inflows_paise": stmt.operating_inflows_paise,
            "operating_outflows_paise": stmt.operating_outflows_paise,
            "net_operating_cash_flow_paise": stmt.net_operating_cash_flow_paise,
            "net_investing_cash_flow_paise": stmt.net_investing_cash_flow_paise,
            "net_financing_cash_flow_paise": stmt.net_financing_cash_flow_paise,
            "net_cash_change_paise": stmt.net_cash_change_paise,
            "opening_cash_balance_paise": stmt.opening_cash_balance_paise,
            "closing_cash_balance_paise": stmt.closing_cash_balance_paise,
            "data_quality_warnings": stmt.data_quality_warnings,
        }
    elif report_type in ["balance_sheet"]:
        target_date = payload.as_of_date or period.end_date
        stmt = await service.generate_balance_sheet(
            workspace_id=context.workspace_id,
            as_of_date=target_date,
        )
        validation_status = "passed" if stmt.is_balanced else "warning"
        report_data_json = {
            "as_of_date": stmt.as_of_date.isoformat(),
            "currency": stmt.currency,
            "total_assets_paise": stmt.total_assets_paise,
            "total_liabilities_paise": stmt.total_liabilities_paise,
            "total_equity_paise": stmt.total_equity_paise,
            "is_balanced": stmt.is_balanced,
            "discrepancy_paise": stmt.discrepancy_paise,
            "asset_lines": [line.__dict__ for line in stmt.asset_lines],
            "liability_lines": [line.__dict__ for line in stmt.liability_lines],
            "equity_lines": [line.__dict__ for line in stmt.equity_lines],
            "validation_notes": stmt.validation_notes,
        }
    elif report_type in ["trial_balance"]:
        target_date = payload.as_of_date or period.end_date
        stmt = await service.generate_trial_balance(
            workspace_id=context.workspace_id,
            as_of_date=target_date,
        )
        validation_status = "passed" if stmt.is_balanced else "warning"
        report_data_json = {
            "as_of_date": stmt.as_of_date.isoformat(),
            "currency": stmt.currency,
            "total_debits_paise": stmt.total_debits_paise,
            "total_credits_paise": stmt.total_credits_paise,
            "is_balanced": stmt.is_balanced,
            "discrepancy_paise": stmt.discrepancy_paise,
            "lines": [line.__dict__ for line in stmt.lines],
        }
    else:
        raise ValidationException(f"Unsupported report type '{payload.report_type}'.")

    # Ensure JSON serializability and calculate SHA256 checksum
    report_data_json = _to_json_safe(report_data_json)
    checksum = hashlib.sha256(str(report_data_json).encode("utf-8")).hexdigest()

    saved_report = await service.report_repo.create_report(
        workspace_id=context.workspace_id,
        report_type=report_type,
        period_type=period.period_type,
        start_date=period.start_date,
        end_date=period.end_date,
        accounting_basis=payload.basis,
        title=title,
        parameters_json=payload.model_dump(mode="json"),
        report_data_json=report_data_json,
        validation_status=validation_status,
        generated_by_id=context.user_id,
        file_format=payload.format,
        checksum=checksum,
    )
    await session.commit()

    return saved_report


@router.get(
    "/reports/history",
    response_model=List[GeneratedReportResponse],
    summary="List generated financial reports history",
)
async def list_report_history(
    report_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    reports = await service.report_repo.list_reports(
        workspace_id=context.workspace_id,
        report_type=report_type,
        limit=limit,
        offset=offset,
    )
    return reports


@router.get(
    "/reports/{report_id}",
    response_model=GeneratedReportResponse,
    summary="Get details of a specific generated report snapshot",
)
async def get_report_snapshot(
    report_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    report = await service.report_repo.get_report(context.workspace_id, report_id)
    if not report:
        raise NotFoundException("Generated report snapshot not found.")
    return report


@router.get(
    "/reports/{report_id}/download",
    summary="Download generated financial report as CSV with formula-injection defenses",
)
async def download_report_csv(
    report_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.EXPORT_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    report = await service.report_repo.get_report(context.workspace_id, report_id)
    if not report:
        raise NotFoundException("Generated report snapshot not found.")

    data = report.report_data_json or {}
    lines_raw = (
        data.get("lines")
        or data.get("income_lines", []) + data.get("expense_lines", [])
        or data.get("asset_lines", []) + data.get("liability_lines", []) + data.get("equity_lines", [])
    )

    statement_lines = [
        StatementLineResponse(**lr) for lr in lines_raw
    ]

    total_inflow = data.get("total_income_paise") or data.get("total_assets_paise") or data.get("total_debits_paise") or 0
    total_outflow = data.get("total_expense_paise") or data.get("total_liabilities_paise") or data.get("total_credits_paise") or 0
    net_result = data.get("net_surplus_deficit_paise") or data.get("total_equity_paise") or 0

    period_vo = service.resolve_reporting_period(
        period_type=report.period_type,
        start_date=report.start_date,
        end_date=report.end_date,
    )

    csv_content = service.export_statement_csv(
        statement_name=report.title,
        period=period_vo,
        currency=data.get("currency", "INR"),
        lines=statement_lines,
        total_inflow_paise=total_inflow,
        total_outflow_paise=total_outflow,
        net_result_paise=net_result,
    )

    filename = f"arthsavora_{report.report_type}_{report.start_date.isoformat()}_{report.end_date.isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Checksum": report.checksum or "",
        },
    )


# ---------------------------------------------------------------------------
# 4. Report Validation Engine
# ---------------------------------------------------------------------------
@router.get(
    "/reports/validation",
    response_model=List[ReportValidationFindingResponse],
    summary="Run and retrieve accounting equality and compliance validation findings",
)
async def get_report_validations(
    fiscal_year: Optional[str] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    period = service.resolve_reporting_period(
        period_type=PeriodType.FINANCIAL_YEAR.value,
        fiscal_year=fiscal_year,
    )
    findings = await service.run_validations(
        workspace_id=context.workspace_id,
        period=period,
    )
    return findings


@router.post(
    "/reports/validation/{finding_id}/resolve",
    response_model=ReportValidationFindingResponse,
    summary="Resolve a validation finding with notes",
)
async def resolve_validation_finding(
    finding_id: UUID,
    payload: ResolveValidationFindingRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.GENERATE_FINANCIAL_REPORTS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    finding = await service.report_repo.resolve_validation_finding(
        workspace_id=context.workspace_id,
        finding_id=finding_id,
        notes=payload.notes,
    )
    if not finding:
        raise NotFoundException("Validation finding not found.")
    await session.commit()
    return finding


# ---------------------------------------------------------------------------
# 5. Tax Intelligence & Classification
# ---------------------------------------------------------------------------
@router.get(
    "/tax/classifications",
    response_model=List[TaxClassificationResponse],
    summary="List transaction tax classifications with review status and category filters",
)
async def list_tax_classifications(
    tax_year: Optional[str] = Query(None),
    tax_category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    classifications = await service.report_repo.list_tax_classifications(
        workspace_id=context.workspace_id,
        tax_year=tax_year,
        tax_category=tax_category,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )
    return classifications


@router.post(
    "/tax/classifications/suggest",
    response_model=List[TaxClassificationResponse],
    summary="Scan unclassified transactions and generate automated tax suggestions",
)
async def suggest_tax_classifications(
    payload: SuggestTaxClassificationsRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    tax_year = payload.tax_year or calculate_indian_financial_year(date.today())
    records = await service.suggest_tax_classifications_for_fy(
        workspace_id=context.workspace_id,
        tax_year=tax_year,
    )
    return records


@router.post(
    "/tax/classifications/{transaction_id}/review",
    response_model=TaxClassificationResponse,
    summary="Review and confirm/modify transaction tax classification",
)
async def review_tax_classification(
    transaction_id: UUID,
    payload: ReviewTaxClassificationRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    rec = await service.review_tax_classification(
        workspace_id=context.workspace_id,
        transaction_id=transaction_id,
        user_id=context.user_id,
        tax_category=payload.tax_category,
        review_status=payload.review_status,
        notes=payload.notes,
    )
    if payload.deductible_amount_paise is not None:
        rec.deductible_amount_paise = payload.deductible_amount_paise
    if payload.evidence_document_id is not None:
        rec.evidence_document_id = payload.evidence_document_id
    await session.commit()
    return rec


# ---------------------------------------------------------------------------
# 6. GST Readiness Summary
# ---------------------------------------------------------------------------
@router.get(
    "/tax/gst-summary",
    response_model=GSTReportSummaryResponse,
    summary="Get GST readiness and turnover summary from business invoices",
)
async def get_gst_summary(
    period_type: str = Query(PeriodType.FINANCIAL_YEAR.value),
    fiscal_year: Optional[str] = Query(None),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    period = service.resolve_reporting_period(
        period_type=period_type,
        fiscal_year=fiscal_year,
        quarter=quarter,
        start_date=start_date,
        end_date=end_date,
    )
    summary = await service.generate_gst_summary(
        workspace_id=context.workspace_id,
        period=period,
    )

    return GSTReportSummaryResponse(
        period=ReportingPeriodResponse(
            period_type=period.period_type,
            fiscal_year=period.fiscal_year,
            quarter=period.quarter,
            start_date=period.start_date,
            end_date=period.end_date,
            label=period.label,
        ),
        currency="INR",
        taxable_turnover_paise=summary.taxable_sales_paise,
        exempt_turnover_paise=summary.exempt_sales_paise,
        total_turnover_paise=summary.total_turnover_paise,
        output_cgst_paise=summary.output_cgst_paise,
        output_sgst_paise=summary.output_sgst_paise,
        output_igst_paise=summary.output_igst_paise,
        total_output_gst_paise=summary.total_output_tax_paise,
        estimated_input_tax_credit_paise=summary.input_tax_recorded_paise,
        estimated_net_gst_payable_paise=summary.estimated_net_tax_liability_paise,
        invoices_analyzed_count=summary.invoices_analyzed_count,
        disclaimer=summary.data_disclaimer,
    )


# ---------------------------------------------------------------------------
# 7. Income Tax Estimation
# ---------------------------------------------------------------------------
@router.get(
    "/tax/estimates",
    response_model=Optional[TaxEstimateResponse],
    summary="Get latest estimated income tax calculation snapshot",
)
async def get_latest_tax_estimate(
    financial_year: Optional[str] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    fy = financial_year or calculate_indian_financial_year(date.today())
    snapshot = await service.report_repo.get_latest_tax_estimate(
        workspace_id=context.workspace_id,
        financial_year=fy,
    )
    if not snapshot:
        return None

    return TaxEstimateResponse(
        financial_year=snapshot.financial_year,
        assessment_year=snapshot.assessment_year,
        taxpayer_category=snapshot.taxpayer_category,
        regime=snapshot.regime,
        gross_income_paise=snapshot.gross_income_paise,
        standard_deduction_paise=7500000 if snapshot.regime == TaxRegime.NEW_REGIME.value else 5000000,
        chapter_via_deductions_paise=snapshot.deductions_paise,
        taxable_income_paise=snapshot.taxable_income_paise,
        slab_tax_paise=snapshot.estimated_tax_paise,
        rebate_87a_paise=0,
        health_education_cess_paise=int(snapshot.estimated_tax_paise * 0.04),
        total_estimated_tax_paise=snapshot.estimated_tax_paise,
        effective_tax_rate_percent=float(snapshot.effective_tax_rate_percent),
        assumptions_narrative=snapshot.assumptions_narrative,
        missing_data_warnings=snapshot.missing_data_warnings or [],
        statutory_disclaimer="ARTHSAVORA Tax Intelligence provides purely mathematical estimations for informational planning. It does not constitute certified tax advice or formal filing.",
    )


@router.post(
    "/tax/estimates",
    response_model=TaxEstimateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate and persist a new Income Tax estimate snapshot",
)
async def create_tax_estimate(
    payload: CreateTaxEstimateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_TAX_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialReportingService(session)
    fy = payload.financial_year or calculate_indian_financial_year(date.today())
    estimate_vo = await service.generate_income_tax_estimate(
        workspace_id=context.workspace_id,
        financial_year=fy,
        regime=payload.regime,
        user_id=context.user_id,
    )

    return TaxEstimateResponse(
        financial_year=estimate_vo.financial_year,
        assessment_year=estimate_vo.assessment_year,
        taxpayer_category=estimate_vo.taxpayer_category,
        regime=estimate_vo.regime,
        gross_income_paise=estimate_vo.gross_total_income_paise,
        standard_deduction_paise=estimate_vo.standard_deduction_paise,
        chapter_via_deductions_paise=estimate_vo.chapter_vi_a_deductions_paise,
        taxable_income_paise=estimate_vo.taxable_income_paise,
        slab_tax_paise=estimate_vo.base_tax_paise,
        rebate_87a_paise=0,
        health_education_cess_paise=estimate_vo.cess_paise,
        total_estimated_tax_paise=estimate_vo.total_estimated_tax_paise,
        effective_tax_rate_percent=float(estimate_vo.effective_tax_rate_percent),
        assumptions_narrative=estimate_vo.assumptions_narrative,
        missing_data_warnings=estimate_vo.missing_data_warnings,
        statutory_disclaimer=estimate_vo.legal_disclaimer,
    )
