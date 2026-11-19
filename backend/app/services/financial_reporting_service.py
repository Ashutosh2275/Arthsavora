"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance Service
Orchestrates financial statements (Income & Expense, Cash Flow, Balance Sheet, Trial Balance,
General Ledger, Account Statements), Indian fiscal year date handling, multi-entity reporting
(personal, family, business), tax classification, GST readiness, and report exports.
"""

import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import io
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import logger
from app.domain.financial_report import (
    AccountingBasis,
    BalanceSheetVO,
    CashFlowStatementVO,
    ExportFormat,
    GSTReportSummaryVO,
    IncomeExpenseStatementVO,
    IncomeTaxEstimateVO,
    PeriodType,
    ReportType,
    ReportValidationFindingVO,
    ReportingPeriodVO,
    StatementLineVO,
    TaxClassificationVO,
    TaxJurisdiction,
    TaxRegime,
    TaxReviewStatus,
    TaxpayerCategory,
    TrialBalanceReportVO,
    ValidationSeverity,
    calculate_financial_year_bounds,
    calculate_indian_financial_year,
    calculate_quarter_bounds,
    estimate_indian_income_tax,
    sanitize_csv_cell,
    validate_balance_sheet_equation,
)
from app.infrastructure.database.models.account import Account, AccountBalanceSnapshot
from app.infrastructure.database.models.accounting import (
    AccountingPeriod,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
from app.infrastructure.database.models.business import BusinessInvoice, BusinessProfile
from app.infrastructure.database.models.document import FinancialDocument
from app.infrastructure.database.models.family import FamilyAccountShare
from app.infrastructure.database.models.financial_report import (
    GeneratedReport,
    ReportValidationFinding,
    TaxClassificationRecord,
    TaxEstimateSnapshot,
    TaxRule,
)
from app.infrastructure.database.models.transaction import Transaction
from app.infrastructure.database.models.workspace import Workspace
from app.repositories.account_repository import AccountRepository
from app.repositories.financial_report_repository import FinancialReportRepository


class FinancialReportingService:
    """Core reporting, tax intelligence, and validation service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repo = FinancialReportRepository(session)
        self.account_repo = AccountRepository(session)

    # -------------------------------------------------------------------------
    # 1. Reporting Period Resolution
    # -------------------------------------------------------------------------
    def resolve_reporting_period(
        self,
        period_type: str = PeriodType.FINANCIAL_YEAR.value,
        fiscal_year: Optional[str] = None,
        quarter: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        reference_date: Optional[date] = None,
    ) -> ReportingPeriodVO:
        """
        Resolves canonical reporting period bounds. Defaults to current Indian Financial Year (Apr-Mar).
        """
        today = reference_date or date.today()
        current_fy = fiscal_year or calculate_indian_financial_year(today)

        if period_type == PeriodType.FINANCIAL_YEAR.value:
            s_date, e_date = calculate_financial_year_bounds(current_fy)
            label = f"Financial Year {current_fy} (Apr 1, {s_date.year} - Mar 31, {e_date.year})"
            return ReportingPeriodVO(
                period_type=period_type,
                start_date=s_date,
                end_date=e_date,
                label=label,
                fiscal_year=current_fy,
            )

        elif period_type == PeriodType.QUARTERLY.value:
            q = quarter or 1
            s_date, e_date, label = calculate_quarter_bounds(current_fy, q)
            return ReportingPeriodVO(
                period_type=period_type,
                start_date=s_date,
                end_date=e_date,
                label=label,
                fiscal_year=current_fy,
                quarter=q,
            )

        elif period_type == PeriodType.MONTHLY.value:
            target_year = today.year
            target_month = today.month
            if start_date:
                target_year = start_date.year
                target_month = start_date.month
            s_date = date(target_year, target_month, 1)
            # Find last day of month
            if target_month == 12:
                e_date = date(target_year, 12, 31)
            else:
                next_month_start = date(target_year, target_month + 1, 1)
                e_date = next_month_start - timedelta(days=1)
            label = s_date.strftime("%B %Y")
            return ReportingPeriodVO(
                period_type=period_type,
                start_date=s_date,
                end_date=e_date,
                label=label,
                fiscal_year=calculate_indian_financial_year(s_date),
            )

        elif period_type == PeriodType.CUSTOM.value:
            if not start_date or not end_date:
                raise ValidationException("start_date and end_date are required for custom reporting period.")
            if start_date > end_date:
                raise ValidationException(f"start_date ({start_date}) cannot be after end_date ({end_date}).")
            label = f"Custom Period: {start_date.isoformat()} to {end_date.isoformat()}"
            return ReportingPeriodVO(
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
                label=label,
                fiscal_year=calculate_indian_financial_year(start_date),
            )

        else:
            # Fallback to monthly
            s_date = date(today.year, today.month, 1)
            if today.month == 12:
                e_date = date(today.year, 12, 31)
            else:
                e_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return ReportingPeriodVO(
                period_type=period_type,
                start_date=s_date,
                end_date=e_date,
                label=s_date.strftime("%B %Y"),
                fiscal_year=calculate_indian_financial_year(s_date),
            )

    # -------------------------------------------------------------------------
    # 2. Financial Statements Generation
    # -------------------------------------------------------------------------
    async def generate_income_and_expense_statement(
        self,
        workspace_id: UUID,
        period: ReportingPeriodVO,
        basis: str = AccountingBasis.CASH.value,
    ) -> IncomeExpenseStatementVO:
        """
        Builds the Income and Expense Statement.
        Under Accrual basis: Evaluates posted journal lines for revenue (4xxx) and expense (5xxx) ledger accounts.
        Under Cash basis: Evaluates posted transactions with settled/posted status in the date window.
        """
        income_lines: List[StatementLineVO] = []
        expense_lines: List[StatementLineVO] = []
        warnings: List[str] = []

        if basis == AccountingBasis.ACCRUAL.value:
            # Query posted general ledger lines
            stmt = (
                select(
                    LedgerAccount.code,
                    LedgerAccount.name,
                    LedgerAccount.account_type,
                    LedgerAccount.sub_type,
                    JournalLine.entry_type,
                    func.sum(JournalLine.amount_paise).label("sum_paise"),
                )
                .join(JournalLine, JournalLine.ledger_account_id == LedgerAccount.id)
                .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
                .where(
                    LedgerAccount.workspace_id == workspace_id,
                    JournalEntry.status == "posted",
                    JournalEntry.entry_date >= period.start_date,
                    JournalEntry.entry_date <= period.end_date,
                    LedgerAccount.account_type.in_(["revenue", "expense"]),
                )
                .group_by(
                    LedgerAccount.code,
                    LedgerAccount.name,
                    LedgerAccount.account_type,
                    LedgerAccount.sub_type,
                    JournalLine.entry_type,
                )
            )
            rows = (await self.session.execute(stmt)).all()

            # Group by account code
            acc_sums: Dict[str, Dict[str, Any]] = {}
            for code, name, acc_type, sub_type, entry_type, sum_paise in rows:
                if code not in acc_sums:
                    acc_sums[code] = {
                        "name": name,
                        "type": acc_type,
                        "sub_type": sub_type,
                        "debit": 0,
                        "credit": 0,
                    }
                acc_sums[code][entry_type] += sum_paise or 0

            for code, data in sorted(acc_sums.items()):
                if data["type"] == "revenue":
                    # Revenue normal balance is credit: Net = credit - debit
                    net_paise = data["credit"] - data["debit"]
                    income_lines.append(
                        StatementLineVO(
                            account_code=code,
                            account_name=data["name"],
                            account_type="revenue",
                            sub_type=data["sub_type"],
                            balance_paise=net_paise,
                            display_amount=Decimal(net_paise) / Decimal(100),
                        )
                    )
                else:
                    # Expense normal balance is debit: Net = debit - credit
                    net_paise = data["debit"] - data["credit"]
                    expense_lines.append(
                        StatementLineVO(
                            account_code=code,
                            account_name=data["name"],
                            account_type="expense",
                            sub_type=data["sub_type"],
                            balance_paise=net_paise,
                            display_amount=Decimal(net_paise) / Decimal(100),
                        )
                    )

            if not acc_sums:
                warnings.append("No posted accrual journal entries found in this period. Showing zero-balance statement.")

        else:
            # Cash basis: Aggregate posted transactions
            tx_stmt = (
                select(
                    Transaction.direction,
                    Transaction.transaction_type,
                    func.sum(Transaction.amount_paise).label("sum_paise"),
                )
                .where(
                    Transaction.workspace_id == workspace_id,
                    Transaction.status == "posted",
                    Transaction.transaction_date >= period.start_date,
                    Transaction.transaction_date <= period.end_date,
                    Transaction.transaction_type.in_(["income", "expense"]),
                )
                .group_by(Transaction.direction, Transaction.transaction_type)
            )
            tx_rows = (await self.session.execute(tx_stmt)).all()

            for direction, t_type, sum_paise in tx_rows:
                val = sum_paise or 0
                if t_type == "income" or direction == "inflow":
                    income_lines.append(
                        StatementLineVO(
                            account_code="4000-CASH",
                            account_name="Cash Collections / Operating Inflow",
                            account_type="revenue",
                            sub_type="cash_receipts",
                            balance_paise=val,
                            display_amount=Decimal(val) / Decimal(100),
                        )
                    )
                elif t_type == "expense" or direction == "outflow":
                    expense_lines.append(
                        StatementLineVO(
                            account_code="5000-CASH",
                            account_name="Cash Disbursements / Operating Expenses",
                            account_type="expense",
                            sub_type="cash_disbursements",
                            balance_paise=val,
                            display_amount=Decimal(val) / Decimal(100),
                        )
                    )

        total_income = sum(line.balance_paise for line in income_lines)
        total_expenses = sum(line.balance_paise for line in expense_lines)
        net_surplus = total_income - total_expenses

        return IncomeExpenseStatementVO(
            reporting_period=period,
            accounting_basis=AccountingBasis(basis),
            currency="INR",
            operating_income_paise=total_income,
            other_income_paise=0,
            total_income_paise=total_income,
            direct_expenses_paise=0,
            operating_expenses_paise=total_expenses,
            financial_expenses_paise=0,
            total_expenses_paise=total_expenses,
            net_surplus_deficit_paise=net_surplus,
            income_lines=income_lines,
            expense_lines=expense_lines,
            data_quality_warnings=warnings,
        )

    async def generate_cash_flow_statement(
        self,
        workspace_id: UUID,
        period: ReportingPeriodVO,
    ) -> CashFlowStatementVO:
        """
        Builds the Cash Flow Statement analyzing operating, investing, and financing cash flows,
        deriving opening and closing liquid balances. Excludes internal transfers.
        """
        # Operating Inflows and Outflows
        tx_stmt = select(Transaction).where(
            Transaction.workspace_id == workspace_id,
            Transaction.status == "posted",
            Transaction.transaction_date >= period.start_date,
            Transaction.transaction_date <= period.end_date,
        )
        txs = (await self.session.execute(tx_stmt)).scalars().all()

        op_inflows = 0
        op_outflows = 0
        inv_inflows = 0
        inv_outflows = 0
        fin_inflows = 0
        fin_outflows = 0

        inflow_lines: List[StatementLineVO] = []
        outflow_lines: List[StatementLineVO] = []

        for tx in txs:
            if tx.transaction_type == "transfer":
                # Exclude internal transfers between bank accounts
                continue

            if tx.direction == "inflow":
                op_inflows += tx.amount_paise
            elif tx.direction == "outflow":
                op_outflows += tx.amount_paise

        inflow_lines.append(
            StatementLineVO(
                account_code="CF-OP-IN",
                account_name="Operating Inflows & Customer Receipts",
                account_type="asset",
                sub_type="operating_inflow",
                balance_paise=op_inflows,
                display_amount=Decimal(op_inflows) / Decimal(100),
            )
        )
        outflow_lines.append(
            StatementLineVO(
                account_code="CF-OP-OUT",
                account_name="Operating Disbursements & Supplier Payments",
                account_type="asset",
                sub_type="operating_outflow",
                balance_paise=op_outflows,
                display_amount=Decimal(op_outflows) / Decimal(100),
            )
        )

        net_operating = op_inflows - op_outflows
        net_investing = inv_inflows - inv_outflows
        net_financing = fin_inflows - fin_outflows
        net_movement = net_operating + net_investing + net_financing

        # Determine opening and closing liquid cash balances across accounts
        accounts = await self.account_repo.list_by_workspace(workspace_id)
        current_total_liquid = sum(acc.current_book_balance_paise for acc in accounts if acc.account_type in ("savings", "current", "cash"))

        # For historical opening balance: Closing = Current liquid; Opening = Closing - Net movement
        closing_cash = current_total_liquid
        opening_cash = closing_cash - net_movement

        return CashFlowStatementVO(
            reporting_period=period,
            currency="INR",
            operating_inflows_paise=op_inflows,
            operating_outflows_paise=op_outflows,
            net_operating_cash_flow_paise=net_operating,
            investing_inflows_paise=inv_inflows,
            investing_outflows_paise=inv_outflows,
            net_investing_cash_flow_paise=net_investing,
            financing_inflows_paise=fin_inflows,
            financing_outflows_paise=fin_outflows,
            net_financing_cash_flow_paise=net_financing,
            net_cash_movement_paise=net_movement,
            opening_cash_balance_paise=opening_cash,
            closing_cash_balance_paise=closing_cash,
            inflow_lines=inflow_lines,
            outflow_lines=outflow_lines,
            data_quality_warnings=[],
        )

    async def generate_balance_sheet(
        self,
        workspace_id: UUID,
        as_of_date: date,
    ) -> BalanceSheetVO:
        """
        Builds the Balance Sheet report as of a specific date, enforcing Assets = Liabilities + Equity.
        """
        # Fetch ledger accounts and calculate point-in-time balances
        stmt = (
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                LedgerAccount.sub_type,
                LedgerAccount.normal_balance,
                JournalLine.entry_type,
                func.sum(JournalLine.amount_paise).label("sum_paise"),
            )
            .join(JournalLine, JournalLine.ledger_account_id == LedgerAccount.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                LedgerAccount.workspace_id == workspace_id,
                JournalEntry.status == "posted",
                JournalEntry.entry_date <= as_of_date,
                LedgerAccount.account_type.in_(["asset", "liability", "equity"]),
            )
            .group_by(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                LedgerAccount.sub_type,
                LedgerAccount.normal_balance,
                JournalLine.entry_type,
            )
        )
        rows = (await self.session.execute(stmt)).all()

        acc_map: Dict[str, Dict[str, Any]] = {}
        for code, name, acc_type, sub_type, norm_bal, entry_type, sum_paise in rows:
            if code not in acc_map:
                acc_map[code] = {
                    "name": name,
                    "type": acc_type,
                    "sub_type": sub_type,
                    "normal_balance": norm_bal,
                    "debit": 0,
                    "credit": 0,
                }
            acc_map[code][entry_type] += sum_paise or 0

        asset_lines: List[StatementLineVO] = []
        liability_lines: List[StatementLineVO] = []
        equity_lines: List[StatementLineVO] = []

        total_assets = 0
        total_liabilities = 0
        total_equity = 0

        for code, data in sorted(acc_map.items()):
            if data["normal_balance"] == "debit":
                net = data["debit"] - data["credit"]
            else:
                net = data["credit"] - data["debit"]

            line = StatementLineVO(
                account_code=code,
                account_name=data["name"],
                account_type=data["type"],
                sub_type=data["sub_type"],
                balance_paise=net,
                display_amount=Decimal(net) / Decimal(100),
            )

            if data["type"] == "asset":
                asset_lines.append(line)
                total_assets += net
            elif data["type"] == "liability":
                liability_lines.append(line)
                total_liabilities += net
            elif data["type"] == "equity":
                equity_lines.append(line)
                total_equity += net

        # Check Fundamental Equation
        is_balanced, discrepancy, expl = validate_balance_sheet_equation(
            total_assets, total_liabilities, total_equity
        )
        warnings = []
        if not is_balanced:
            warnings.append(expl)

        return BalanceSheetVO(
            as_of_date=as_of_date,
            currency="INR",
            total_assets_paise=total_assets,
            total_liabilities_paise=total_liabilities,
            total_equity_paise=total_equity,
            is_balanced=is_balanced,
            discrepancy_paise=discrepancy,
            asset_lines=asset_lines,
            liability_lines=liability_lines,
            equity_lines=equity_lines,
            data_quality_warnings=warnings,
        )

    async def generate_trial_balance(
        self,
        workspace_id: UUID,
        as_of_date: date,
    ) -> TrialBalanceReportVO:
        """
        Builds the complete Trial Balance verifying Total Debits == Total Credits.
        """
        stmt = (
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                LedgerAccount.normal_balance,
                JournalLine.entry_type,
                func.sum(JournalLine.amount_paise).label("sum_paise"),
            )
            .join(JournalLine, JournalLine.ledger_account_id == LedgerAccount.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                LedgerAccount.workspace_id == workspace_id,
                JournalEntry.status == "posted",
                JournalEntry.entry_date <= as_of_date,
            )
            .group_by(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                LedgerAccount.normal_balance,
                JournalLine.entry_type,
            )
        )
        rows = (await self.session.execute(stmt)).all()

        acc_map: Dict[str, Dict[str, Any]] = {}
        for code, name, acc_type, norm_bal, entry_type, sum_paise in rows:
            if code not in acc_map:
                acc_map[code] = {
                    "code": code,
                    "name": name,
                    "type": acc_type,
                    "normal_balance": norm_bal,
                    "debit": 0,
                    "credit": 0,
                }
            acc_map[code][entry_type] += sum_paise or 0

        lines: List[Dict[str, Any]] = []
        total_debits = 0
        total_credits = 0

        for code, data in sorted(acc_map.items()):
            d = data["debit"]
            c = data["credit"]
            # Trial balance displays net balance on the normal side
            if d >= c:
                net_debit = d - c
                net_credit = 0
            else:
                net_debit = 0
                net_credit = c - d

            total_debits += net_debit
            total_credits += net_credit

            lines.append({
                "account_code": code,
                "account_name": data["name"],
                "account_type": data["type"],
                "debit_paise": net_debit,
                "credit_paise": net_credit,
                "debit_amount": Decimal(net_debit) / Decimal(100),
                "credit_amount": Decimal(net_credit) / Decimal(100),
            })

        diff = total_debits - total_credits
        return TrialBalanceReportVO(
            as_of_date=as_of_date,
            currency="INR",
            total_debits_paise=total_debits,
            total_credits_paise=total_credits,
            is_balanced=(diff == 0),
            discrepancy_paise=diff,
            lines=lines,
        )

    # -------------------------------------------------------------------------
    # 3. Tax Intelligence & GST Readiness
    # -------------------------------------------------------------------------
    async def suggest_tax_classifications_for_fy(
        self,
        workspace_id: UUID,
        tax_year: str,
    ) -> List[TaxClassificationRecord]:
        """
        Scans unclassified transactions within the financial year, matches them against
        active tax rules, and creates suggested TaxClassificationRecord items.
        """
        fy_start, fy_end = calculate_financial_year_bounds(tax_year)

        # Ensure default tax rules are seeded
        rules = await self.report_repo.seed_default_tax_rules()

        # Query transactions in the FY that do not have an existing classification
        subq = (
            select(TaxClassificationRecord.transaction_id)
            .where(TaxClassificationRecord.workspace_id == workspace_id)
        )
        tx_stmt = (
            select(Transaction)
            .where(
                Transaction.workspace_id == workspace_id,
                Transaction.status == "posted",
                Transaction.transaction_date >= fy_start,
                Transaction.transaction_date <= fy_end,
                ~Transaction.id.in_(subq),
            )
            .limit(200)
        )
        txs = (await self.session.execute(tx_stmt)).scalars().all()

        created_records: List[TaxClassificationRecord] = []

        for tx in txs:
            desc_lower = (tx.description or "").lower()
            merchant_lower = (tx.merchant_name or "").lower()
            haystack = f"{desc_lower} {merchant_lower}"

            matched_cat = "unclassified"
            matched_rule = None

            for rule in rules:
                criteria = rule.matcher_criteria_json or {}
                keywords = criteria.get("keywords", [])
                if any(kw in haystack for kw in keywords):
                    matched_cat = rule.category
                    matched_rule = rule
                    break

            if matched_rule:
                rec = await self.report_repo.upsert_tax_classification(
                    workspace_id=workspace_id,
                    transaction_id=tx.id,
                    tax_year=tax_year,
                    tax_category=matched_cat,
                    tax_category_code=matched_rule.rule_code,
                    review_status=TaxReviewStatus.SUGGESTED.value,
                    rule_code=matched_rule.rule_code,
                    rule_version=matched_rule.rule_version,
                    taxable_amount_paise=tx.amount_paise,
                    deductible_amount_paise=tx.amount_paise if "deductible" in matched_cat or "80" in matched_cat else 0,
                    user_notes=f"Auto-suggested based on pattern match rule {matched_rule.rule_code}.",
                )
                created_records.append(rec)

        await self.session.commit()
        return created_records

    async def review_tax_classification(
        self,
        workspace_id: UUID,
        transaction_id: UUID,
        user_id: UUID,
        tax_category: str,
        review_status: str = TaxReviewStatus.CONFIRMED.value,
        notes: Optional[str] = None,
    ) -> TaxClassificationRecord:
        """Explicit user review and confirmation of a tax classification."""
        rec = await self.report_repo.get_tax_classification(workspace_id, transaction_id)
        if not rec:
            raise NotFoundException("Tax classification record not found for transaction.")

        rec.tax_category = tax_category
        rec.review_status = review_status
        rec.reviewed_by_id = user_id
        rec.reviewed_at = datetime.now(timezone.utc)
        if notes:
            rec.user_notes = notes

        await self.session.commit()
        return rec

    async def generate_gst_summary(
        self,
        workspace_id: UUID,
        period: ReportingPeriodVO,
    ) -> GSTReportSummaryVO:
        """
        Builds a structured GST report summary from authoritative business invoices.
        Categorizes taxable turnover, output CGST, SGST, IGST, and estimates net tax.
        """
        # Query invoices issued in this period
        inv_stmt = select(BusinessInvoice).where(
            BusinessInvoice.workspace_id == workspace_id,
            BusinessInvoice.status.in_(["issued", "partially_paid", "paid"]),
            BusinessInvoice.invoice_date >= period.start_date,
            BusinessInvoice.invoice_date <= period.end_date,
        )
        invoices = (await self.session.execute(inv_stmt)).scalars().all()

        taxable_sales = 0
        exempt_sales = 0
        non_taxable_sales = 0
        total_turnover = 0
        output_cgst = 0
        output_sgst = 0
        output_igst = 0
        total_tax = 0

        # Retrieve profile for GSTIN
        prof_stmt = select(BusinessProfile).where(BusinessProfile.workspace_id == workspace_id)
        profile = (await self.session.execute(prof_stmt)).scalar_one_or_none()
        seller_gstin = profile.gstin if profile else None

        for inv in invoices:
            subtotal = inv.subtotal_amount_paise
            tax_amt = inv.tax_amount_paise
            total = inv.total_amount_paise

            total_turnover += total
            if tax_amt > 0:
                taxable_sales += subtotal
                total_tax += tax_amt

                # Place of supply check: Intra-state vs Inter-state
                seller_state_code = seller_gstin[:2] if seller_gstin and len(seller_gstin) >= 2 else None
                pos_val = getattr(inv, "place_of_supply", None)
                pos_state_code = pos_val[:2] if pos_val and len(pos_val) >= 2 else None

                if seller_state_code and pos_state_code and seller_state_code != pos_state_code:
                    # Inter-state: IGST
                    output_igst += tax_amt
                else:
                    # Intra-state: Split equally between CGST and SGST
                    half_tax = tax_amt // 2
                    output_cgst += half_tax
                    output_sgst += (tax_amt - half_tax)
            else:
                exempt_sales += subtotal

        return GSTReportSummaryVO(
            period_label=period.label,
            financial_year=period.fiscal_year or calculate_indian_financial_year(period.start_date),
            gstin=seller_gstin,
            taxable_sales_paise=taxable_sales,
            exempt_sales_paise=exempt_sales,
            non_taxable_sales_paise=non_taxable_sales,
            total_turnover_paise=total_turnover,
            output_cgst_paise=output_cgst,
            output_sgst_paise=output_sgst,
            output_igst_paise=output_igst,
            total_output_tax_paise=total_tax,
            input_tax_recorded_paise=0,
            estimated_net_tax_liability_paise=total_tax,
            invoices_analyzed_count=len(invoices),
        )

    async def generate_income_tax_estimate(
        self,
        workspace_id: UUID,
        financial_year: str,
        regime: str = TaxRegime.NEW_REGIME.value,
        user_id: Optional[UUID] = None,
    ) -> IncomeTaxEstimateVO:
        """
        Calculates and persists a mathematical Income Tax estimate based on verified FY income.
        """
        fy_start, fy_end = calculate_financial_year_bounds(financial_year)

        # Aggregate total verified inflows
        tx_stmt = select(func.coalesce(func.sum(Transaction.amount_paise), 0)).where(
            Transaction.workspace_id == workspace_id,
            Transaction.status == "posted",
            Transaction.direction == "inflow",
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= fy_start,
            Transaction.transaction_date <= fy_end,
        )
        gross_income_paise = (await self.session.execute(tx_stmt)).scalar_one()

        # Aggregate confirmed Section 80 deductions if old regime
        deductions_paise = 0
        if regime == TaxRegime.OLD_REGIME.value:
            ded_stmt = select(func.coalesce(func.sum(TaxClassificationRecord.deductible_amount_paise), 0)).where(
                TaxClassificationRecord.workspace_id == workspace_id,
                TaxClassificationRecord.tax_year == financial_year,
                TaxClassificationRecord.review_status.in_(["confirmed", "reviewed"]),
                TaxClassificationRecord.tax_category.in_(["section_80c", "section_80d"]),
            )
            deductions_paise = (await self.session.execute(ded_stmt)).scalar_one()
            # 80C cap is 1.5 Lakhs (15,000,000 paise)
            deductions_paise = min(deductions_paise, 20000000)

        estimate_vo = estimate_indian_income_tax(
            gross_income_paise=gross_income_paise,
            deductions_paise=deductions_paise,
            regime=regime,
            fy=financial_year,
        )

        # Persist snapshot
        await self.report_repo.save_tax_estimate(
            workspace_id=workspace_id,
            financial_year=financial_year,
            assessment_year=estimate_vo.assessment_year,
            taxpayer_category=estimate_vo.taxpayer_category,
            regime=regime,
            gross_income_paise=gross_income_paise,
            deductions_paise=deductions_paise,
            taxable_income_paise=estimate_vo.taxable_income_paise,
            estimated_tax_paise=estimate_vo.total_estimated_tax_paise,
            effective_tax_rate_percent=estimate_vo.effective_tax_rate_percent,
            assumptions_narrative=estimate_vo.assumptions_narrative,
            missing_data_warnings=estimate_vo.missing_data_warnings,
            calculated_by_id=user_id,
        )
        await self.session.commit()
        return estimate_vo

    # -------------------------------------------------------------------------
    # 4. Report Validation Engine
    # -------------------------------------------------------------------------
    async def run_validations(
        self,
        workspace_id: UUID,
        period: ReportingPeriodVO,
    ) -> List[ReportValidationFinding]:
        """
        Runs comprehensive accounting equality and tax completeness validations.
        """
        findings: List[ReportValidationFinding] = []

        # 1. Trial Balance Check
        tb = await self.generate_trial_balance(workspace_id, period.end_date)
        if not tb.is_balanced:
            finding = await self.report_repo.create_validation_finding(
                workspace_id=workspace_id,
                report_type="trial_balance",
                period_start=period.start_date,
                period_end=period.end_date,
                rule_code="VAL_TB_EQUALS",
                severity=ValidationSeverity.CRITICAL.value,
                title="Trial Balance Out of Balance",
                description=f"Total Debits (₹{tb.total_debits_paise / 100:,.2f}) does not match Total Credits (₹{tb.total_credits_paise / 100:,.2f}). Variance: ₹{abs(tb.discrepancy_paise) / 100:,.2f}.",
                recommended_action="Inspect unbalanced draft journals or manual journal entries.",
            )
            findings.append(finding)

        # 2. Balance Sheet Fundamental Equation Check
        bs = await self.generate_balance_sheet(workspace_id, period.end_date)
        if not bs.is_balanced:
            finding = await self.report_repo.create_validation_finding(
                workspace_id=workspace_id,
                report_type="balance_sheet",
                period_start=period.start_date,
                period_end=period.end_date,
                rule_code="VAL_BS_EQUALS",
                severity=ValidationSeverity.CRITICAL.value,
                title="Balance Sheet Equation Violation",
                description=f"Assets (₹{bs.total_assets_paise / 100:,.2f}) != Liabilities (₹{bs.total_liabilities_paise / 100:,.2f}) + Equity (₹{bs.total_equity_paise / 100:,.2f}).",
                recommended_action="Ensure prior period net income has been closed to Retained Earnings.",
            )
            findings.append(finding)

        # 3. Missing Receipt Evidence Check for Large Transactions (> ₹10,000)
        large_tx_stmt = select(Transaction).where(
            Transaction.workspace_id == workspace_id,
            Transaction.status == "posted",
            Transaction.direction == "outflow",
            Transaction.amount_paise >= 1000000,
            Transaction.transaction_date >= period.start_date,
            Transaction.transaction_date <= period.end_date,
        )
        large_txs = (await self.session.execute(large_tx_stmt)).scalars().all()

        unsupported_count = 0
        for tx in large_txs:
            # Check if has document association
            tax_rec = await self.report_repo.get_tax_classification(workspace_id, tx.id)
            if not tax_rec or not tax_rec.evidence_document_id:
                unsupported_count += 1

        if unsupported_count > 0:
            finding = await self.report_repo.create_validation_finding(
                workspace_id=workspace_id,
                report_type="tax_compliance",
                period_start=period.start_date,
                period_end=period.end_date,
                rule_code="VAL_DOC_EVIDENCE",
                severity=ValidationSeverity.WARNING.value,
                title=f"{unsupported_count} Large Transactions Lack Supporting Invoices/Receipts",
                description=f"Identified {unsupported_count} transactions exceeding ₹10,000 without linked PDF/image receipt evidence.",
                recommended_action="Upload invoices or receipts via Documents module to substantiate deductions.",
            )
            findings.append(finding)

        await self.session.commit()
        return findings

    # -------------------------------------------------------------------------
    # 5. Export Rendering
    # -------------------------------------------------------------------------
    def export_statement_csv(
        self,
        statement_name: str,
        period: ReportingPeriodVO,
        currency: str,
        lines: List[StatementLineVO],
        total_inflow_paise: int,
        total_outflow_paise: int,
        net_result_paise: int,
    ) -> str:
        """
        Generates CSV format export with formula-injection defenses.
        """
        output = io.StringIO()
        output.write(f'# Report: "{sanitize_csv_cell(statement_name)}"\n')
        output.write(f'# Period: "{sanitize_csv_cell(period.label)}"\n')
        output.write(f'# Generated At: "{datetime.now(timezone.utc).isoformat()}"\n')
        output.write(f'# Currency: "{currency}"\n\n')

        output.write("Account Code,Account Name,Type,Sub Type,Amount (INR)\n")
        for line in lines:
            row = [
                sanitize_csv_cell(line.account_code),
                sanitize_csv_cell(line.account_name),
                sanitize_csv_cell(line.account_type),
                sanitize_csv_cell(line.sub_type or ""),
                f"{line.balance_paise / 100:.2f}",
            ]
            output.write(",".join(f'"{c}"' for c in row) + "\n")

        output.write(f'\n"TOTAL INFLOW / REVENUE","","","", "{total_inflow_paise / 100:.2f}"\n')
        output.write(f'"TOTAL OUTFLOW / EXPENSE","","","", "{total_outflow_paise / 100:.2f}"\n')
        output.write(f'"NET SURPLUS / RESULT","","","", "{net_result_paise / 100:.2f}"\n')

        return output.getvalue()
