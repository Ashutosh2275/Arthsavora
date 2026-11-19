"""
ARTHSAVORA Financial Reporting, Tax Intelligence & Compliance Repository
Persistence management for generated report snapshots, tax classification records,
rule version catalogs, tax estimate snapshots, and validation audit findings.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.financial_report import (
    AccountingBasis,
    ReportType,
    TaxJurisdiction,
    TaxRegime,
    TaxReviewStatus,
    TaxpayerCategory,
    ValidationSeverity,
)
from app.infrastructure.database.models.financial_report import (
    GeneratedReport,
    ReportValidationFinding,
    TaxClassificationRecord,
    TaxEstimateSnapshot,
    TaxRule,
)


class FinancialReportRepository:
    """Handles persistence operations for reports, tax intelligence, and validation records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # 1. Report Snapshots & History
    # -------------------------------------------------------------------------
    async def create_report(
        self,
        workspace_id: UUID,
        report_type: str,
        period_type: str,
        start_date: date,
        end_date: date,
        accounting_basis: str,
        title: str,
        parameters_json: Dict[str, Any],
        report_data_json: Dict[str, Any],
        validation_status: str = "passed",
        generated_by_id: Optional[UUID] = None,
        file_format: Optional[str] = None,
        export_file_path: Optional[str] = None,
        checksum: Optional[str] = None,
    ) -> GeneratedReport:
        """Persists an immutable historical snapshot of a generated financial report."""
        report = GeneratedReport(
            id=uuid4(),
            workspace_id=workspace_id,
            report_type=report_type,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            accounting_basis=accounting_basis,
            title=title,
            parameters_json=parameters_json,
            report_data_json=report_data_json,
            validation_status=validation_status,
            generated_by_id=generated_by_id,
            file_format=file_format,
            export_file_path=export_file_path,
            checksum=checksum,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_report(self, workspace_id: UUID, report_id: UUID) -> Optional[GeneratedReport]:
        """Anti-IDOR query retrieving report by ID within the tenant workspace."""
        stmt = (
            select(GeneratedReport)
            .options(selectinload(GeneratedReport.generated_by))
            .where(
                GeneratedReport.workspace_id == workspace_id,
                GeneratedReport.id == report_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_reports(
        self,
        workspace_id: UUID,
        report_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GeneratedReport]:
        """Lists generated report history for workspace with pagination."""
        stmt = (
            select(GeneratedReport)
            .where(GeneratedReport.workspace_id == workspace_id)
            .order_by(desc(GeneratedReport.created_at))
        )
        if report_type:
            stmt = stmt.where(GeneratedReport.report_type == report_type)
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # 2. Tax Classification Records
    # -------------------------------------------------------------------------
    async def upsert_tax_classification(
        self,
        workspace_id: UUID,
        transaction_id: UUID,
        tax_year: str,
        tax_category: str,
        tax_category_code: str,
        review_status: str,
        rule_code: Optional[str] = None,
        rule_version: Optional[str] = None,
        taxable_amount_paise: int = 0,
        deductible_amount_paise: int = 0,
        tax_rate_percent: Optional[Decimal] = None,
        tax_amount_paise: int = 0,
        gst_component: Optional[str] = None,
        hsn_sac_code: Optional[str] = None,
        evidence_document_id: Optional[UUID] = None,
        reviewed_by_id: Optional[UUID] = None,
        reviewed_at: Optional[datetime] = None,
        user_notes: Optional[str] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> TaxClassificationRecord:
        """Upserts a transaction tax classification record within the tenant boundary."""
        stmt = select(TaxClassificationRecord).where(
            TaxClassificationRecord.workspace_id == workspace_id,
            TaxClassificationRecord.transaction_id == transaction_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.tax_year = tax_year
            existing.tax_category = tax_category
            existing.tax_category_code = tax_category_code
            existing.review_status = review_status
            existing.rule_code = rule_code
            existing.rule_version = rule_version
            existing.taxable_amount_paise = taxable_amount_paise
            existing.deductible_amount_paise = deductible_amount_paise
            existing.tax_rate_percent = tax_rate_percent
            existing.tax_amount_paise = tax_amount_paise
            existing.gst_component = gst_component
            existing.hsn_sac_code = hsn_sac_code
            if evidence_document_id is not None:
                existing.evidence_document_id = evidence_document_id
            if reviewed_by_id is not None:
                existing.reviewed_by_id = reviewed_by_id
                existing.reviewed_at = reviewed_at or datetime.now(timezone.utc)
            if user_notes is not None:
                existing.user_notes = user_notes
            if metadata_payload:
                existing.metadata_payload = metadata_payload
            await self.session.flush()
            return existing

        record = TaxClassificationRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            transaction_id=transaction_id,
            tax_year=tax_year,
            tax_category=tax_category,
            tax_category_code=tax_category_code,
            review_status=review_status,
            rule_code=rule_code,
            rule_version=rule_version,
            taxable_amount_paise=taxable_amount_paise,
            deductible_amount_paise=deductible_amount_paise,
            tax_rate_percent=tax_rate_percent,
            tax_amount_paise=tax_amount_paise,
            gst_component=gst_component,
            hsn_sac_code=hsn_sac_code,
            evidence_document_id=evidence_document_id,
            reviewed_by_id=reviewed_by_id,
            reviewed_at=reviewed_at,
            user_notes=user_notes,
            metadata_payload=metadata_payload or {},
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_tax_classification(
        self,
        workspace_id: UUID,
        transaction_id: UUID,
    ) -> Optional[TaxClassificationRecord]:
        """Retrieves tax classification for a specific transaction."""
        stmt = (
            select(TaxClassificationRecord)
            .options(
                selectinload(TaxClassificationRecord.transaction),
                selectinload(TaxClassificationRecord.evidence_document),
            )
            .where(
                TaxClassificationRecord.workspace_id == workspace_id,
                TaxClassificationRecord.transaction_id == transaction_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_tax_classifications(
        self,
        workspace_id: UUID,
        tax_year: Optional[str] = None,
        review_status: Optional[str] = None,
        tax_category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaxClassificationRecord]:
        """Lists tax classifications for workspace with filters."""
        stmt = (
            select(TaxClassificationRecord)
            .options(
                selectinload(TaxClassificationRecord.transaction),
                selectinload(TaxClassificationRecord.evidence_document),
            )
            .where(TaxClassificationRecord.workspace_id == workspace_id)
            .order_by(desc(TaxClassificationRecord.created_at))
        )
        if tax_year:
            stmt = stmt.where(TaxClassificationRecord.tax_year == tax_year)
        if review_status:
            stmt = stmt.where(TaxClassificationRecord.review_status == review_status)
        if tax_category:
            stmt = stmt.where(TaxClassificationRecord.tax_category == tax_category)

        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # 3. Tax Rules Catalog
    # -------------------------------------------------------------------------
    async def list_tax_rules(
        self,
        jurisdiction: str = "IN",
        is_active: bool = True,
    ) -> List[TaxRule]:
        """Lists active tax rules for a jurisdiction."""
        stmt = (
            select(TaxRule)
            .where(
                TaxRule.jurisdiction == jurisdiction,
                TaxRule.is_active == is_active,
            )
            .order_by(TaxRule.rule_code)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def seed_default_tax_rules(self) -> List[TaxRule]:
        """Seeds default Indian tax rules if catalog is empty."""
        stmt = select(func.count(TaxRule.id))
        count = (await self.session.execute(stmt)).scalar_one()
        if count > 0:
            res = await self.session.execute(select(TaxRule))
            return list(res.scalars().all())

        defaults = [
            TaxRule(
                id=uuid4(),
                rule_code="IN_80C_INVESTMENT",
                rule_version="1.0",
                category="section_80c",
                jurisdiction="IN",
                financial_year_applicability="ANY",
                description="Eligible Section 80C deductions (PPF, ELSS, Life Insurance, EPF) capped at ₹1.5L in Old Regime.",
                matcher_criteria_json={"keywords": ["ppf", "elss", "lic", "provident fund", "life insurance", "nps tier 1"]},
                is_active=True,
            ),
            TaxRule(
                id=uuid4(),
                rule_code="IN_80D_HEALTH_INSURANCE",
                rule_version="1.0",
                category="section_80d",
                jurisdiction="IN",
                financial_year_applicability="ANY",
                description="Medical health insurance premiums and preventive health checkups deductible under Section 80D.",
                matcher_criteria_json={"keywords": ["health insurance", "mediclaim", "care health", "star health", "max bupa"]},
                is_active=True,
            ),
            TaxRule(
                id=uuid4(),
                rule_code="IN_BUSINESS_OPEX",
                rule_version="1.0",
                category="business_deductible",
                jurisdiction="IN",
                financial_year_applicability="ANY",
                description="Ordinary and necessary operating expenses incurred exclusively for freelance/business purposes.",
                matcher_criteria_json={"categories": ["software", "office_supplies", "hosting", "consulting", "travel_business"]},
                is_active=True,
            ),
            TaxRule(
                id=uuid4(),
                rule_code="IN_EXEMPT_INCOME",
                rule_version="1.0",
                category="exempt_income",
                jurisdiction="IN",
                financial_year_applicability="ANY",
                description="Agricultural income, PPF maturity, or tax-free allowances under Section 10.",
                matcher_criteria_json={"keywords": ["ppf maturity", "dividend exempt", "tax free"]},
                is_active=True,
            ),
            TaxRule(
                id=uuid4(),
                rule_code="IN_GST_OUTPUT_18",
                rule_version="1.0",
                category="gst_output",
                jurisdiction="IN",
                financial_year_applicability="ANY",
                description="Standard GST 18% (CGST 9% + SGST 9% or IGST 18%) for commercial B2B professional/digital services.",
                matcher_criteria_json={"gst_rate": 18.0},
                is_active=True,
            ),
        ]
        for rule in defaults:
            self.session.add(rule)
        await self.session.flush()
        return defaults

    # -------------------------------------------------------------------------
    # 4. Tax Estimate Snapshots
    # -------------------------------------------------------------------------
    async def save_tax_estimate(
        self,
        workspace_id: UUID,
        financial_year: str,
        assessment_year: str,
        taxpayer_category: str,
        regime: str,
        gross_income_paise: int,
        deductions_paise: int,
        taxable_income_paise: int,
        estimated_tax_paise: int,
        effective_tax_rate_percent: Decimal,
        assumptions_narrative: str,
        missing_data_warnings: List[str],
        calculated_by_id: Optional[UUID] = None,
    ) -> TaxEstimateSnapshot:
        """Saves a point-in-time calculation snapshot of an illustrative tax liability estimate."""
        snapshot = TaxEstimateSnapshot(
            id=uuid4(),
            workspace_id=workspace_id,
            financial_year=financial_year,
            assessment_year=assessment_year,
            taxpayer_category=taxpayer_category,
            regime=regime,
            gross_income_paise=gross_income_paise,
            deductions_paise=deductions_paise,
            taxable_income_paise=taxable_income_paise,
            estimated_tax_paise=estimated_tax_paise,
            effective_tax_rate_percent=effective_tax_rate_percent,
            assumptions_narrative=assumptions_narrative,
            missing_data_warnings=missing_data_warnings,
            calculated_by_id=calculated_by_id,
            calculated_at=datetime.now(timezone.utc),
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest_tax_estimate(
        self,
        workspace_id: UUID,
        financial_year: str,
        regime: Optional[str] = None,
    ) -> Optional[TaxEstimateSnapshot]:
        """Retrieves latest tax estimate snapshot for workspace and fiscal year."""
        stmt = (
            select(TaxEstimateSnapshot)
            .where(
                TaxEstimateSnapshot.workspace_id == workspace_id,
                TaxEstimateSnapshot.financial_year == financial_year,
            )
            .order_by(desc(TaxEstimateSnapshot.calculated_at))
        )
        if regime:
            stmt = stmt.where(TaxEstimateSnapshot.regime == regime)
        stmt = stmt.limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # 5. Report Validation Findings
    # -------------------------------------------------------------------------
    async def create_validation_finding(
        self,
        workspace_id: UUID,
        report_type: str,
        period_start: date,
        period_end: date,
        rule_code: str,
        severity: str,
        title: str,
        description: str,
        affected_entity_id: Optional[str] = None,
        recommended_action: Optional[str] = None,
    ) -> ReportValidationFinding:
        """Persists a data quality discrepancy finding."""
        finding = ReportValidationFinding(
            id=uuid4(),
            workspace_id=workspace_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            rule_code=rule_code,
            severity=severity,
            title=title,
            description=description,
            affected_entity_id=affected_entity_id,
            recommended_action=recommended_action,
            is_resolved=False,
        )
        self.session.add(finding)
        await self.session.flush()
        return finding

    async def list_validation_findings(
        self,
        workspace_id: UUID,
        report_type: Optional[str] = None,
        is_resolved: Optional[bool] = None,
    ) -> List[ReportValidationFinding]:
        """Lists validation findings for workspace."""
        stmt = (
            select(ReportValidationFinding)
            .where(ReportValidationFinding.workspace_id == workspace_id)
            .order_by(desc(ReportValidationFinding.created_at))
        )
        if report_type:
            stmt = stmt.where(ReportValidationFinding.report_type == report_type)
        if is_resolved is not None:
            stmt = stmt.where(ReportValidationFinding.is_resolved == is_resolved)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def resolve_validation_finding(
        self,
        workspace_id: UUID,
        finding_id: UUID,
        resolved_by_id: UUID,
    ) -> Optional[ReportValidationFinding]:
        """Marks a validation finding as resolved with user attribution."""
        stmt = select(ReportValidationFinding).where(
            ReportValidationFinding.workspace_id == workspace_id,
            ReportValidationFinding.id == finding_id,
        )
        finding = (await self.session.execute(stmt)).scalar_one_or_none()
        if finding:
            finding.is_resolved = True
            finding.resolved_at = datetime.now(timezone.utc)
            finding.resolved_by_id = resolved_by_id
            await self.session.flush()
        return finding
