"""
Arthsavora Financial Data Acquisition & Import Repository
PostgreSQL data access layer for ImportJobs, ImportFiles, ImportBatches, and ImportCandidates.
Strict workspace tenancy and anti-IDOR scoping enforced on all operations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.import_types import ImportStatus, ReviewStatus, ValidationStatus
from app.infrastructure.database.models.acquisition import (
    ImportBatch,
    ImportCandidate,
    ImportFile,
    ImportJob,
)


class ImportRepository:
    """Repository managing import lifecycle records and candidate staging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -----------------------------------------------------------------------
    # Import Job Operations
    # -----------------------------------------------------------------------

    async def create_job(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        source_type: str,
        account_id: Optional[uuid.UUID] = None,
        original_filename: Optional[str] = None,
        storage_reference: Optional[str] = None,
        file_checksum: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        processing_metadata: Optional[Dict[str, Any]] = None,
    ) -> ImportJob:
        """Creates an initial import job record."""
        job = ImportJob(
            workspace_id=workspace_id,
            user_id=user_id,
            account_id=account_id,
            source_type=source_type,
            original_filename=original_filename,
            storage_reference=storage_reference,
            file_checksum=file_checksum,
            file_size=file_size,
            mime_type=mime_type,
            status=ImportStatus.UPLOADED.value,
            processing_metadata=processing_metadata or {},
        )
        self.session.add(job)
        await self.session.flush()

        if original_filename and storage_reference and file_checksum and file_size:
            file_record = ImportFile(
                import_job_id=job.id,
                file_name=original_filename,
                file_size=file_size,
                storage_path=storage_reference,
                mime_type=mime_type or "application/octet-stream",
                file_hash=file_checksum,
            )
            self.session.add(file_record)
            await self.session.flush()

        return job

    async def get_job_by_id(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> Optional[ImportJob]:
        """Fetches an import job by ID with strict workspace isolation."""
        stmt = (
            select(ImportJob)
            .where(
                ImportJob.id == job_id,
                ImportJob.workspace_id == workspace_id,
            )
            .options(
                selectinload(ImportJob.files),
                selectinload(ImportJob.batches).selectinload(ImportBatch.candidates),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_job_by_checksum(
        self,
        workspace_id: uuid.UUID,
        file_checksum: str,
    ) -> Optional[ImportJob]:
        """Finds any previous non-failed job in the workspace with identical SHA-256 hash."""
        stmt = select(ImportJob).where(
            ImportJob.workspace_id == workspace_id,
            ImportJob.file_checksum == file_checksum,
            ImportJob.status.in_([
                ImportStatus.COMPLETED.value,
                ImportStatus.CONFIRMED.value,
                ImportStatus.AWAITING_REVIEW.value,
            ]),
        ).order_by(ImportJob.created_at.desc())
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_jobs(
        self,
        workspace_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Tuple[List[ImportJob], int]:
        """Lists paginated import jobs with filters and total count."""
        base_stmt = select(ImportJob).where(ImportJob.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(ImportJob).where(ImportJob.workspace_id == workspace_id)

        if status:
            base_stmt = base_stmt.where(ImportJob.status == status)
            count_stmt = count_stmt.where(ImportJob.status == status)
        if source_type:
            base_stmt = base_stmt.where(ImportJob.source_type == source_type)
            count_stmt = count_stmt.where(ImportJob.source_type == source_type)

        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            base_stmt
            .options(
                selectinload(ImportJob.files),
                selectinload(ImportJob.batches),
            )
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def update_job_status(
        self,
        job: ImportJob,
        status: str,
        total_records: Optional[int] = None,
        valid_records: Optional[int] = None,
        invalid_records: Optional[int] = None,
        duplicate_records: Optional[int] = None,
        imported_records: Optional[int] = None,
        error_summary: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> ImportJob:
        """Updates lifecycle metrics and state transitions on an import job."""
        job.status = status
        if total_records is not None:
            job.total_records = total_records
        if valid_records is not None:
            job.valid_records = valid_records
        if invalid_records is not None:
            job.invalid_records = invalid_records
            job.failed_records = invalid_records
        if duplicate_records is not None:
            job.duplicate_records = duplicate_records
        if imported_records is not None:
            job.imported_records = imported_records
            job.success_records = imported_records
        if error_summary is not None:
            job.error_summary = error_summary
        if completed_at is not None:
            job.completed_at = completed_at
        elif status in (ImportStatus.COMPLETED.value, ImportStatus.PARTIALLY_CONFIRMED.value, ImportStatus.FAILED.value):
            job.completed_at = datetime.now(timezone.utc)

        await self.session.flush()
        return job

    # -----------------------------------------------------------------------
    # Import Batch Operations
    # -----------------------------------------------------------------------

    async def create_batch(
        self,
        import_job_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_format: str,
        sheet_name: Optional[str] = None,
        row_count: int = 0,
        valid_row_count: int = 0,
        invalid_row_count: int = 0,
        duplicate_count: int = 0,
        column_mapping: Optional[Dict[str, str]] = None,
        opening_balance: Optional[Decimal] = None,
        closing_balance: Optional[Decimal] = None,
        calculated_closing_balance: Optional[Decimal] = None,
        reconciliation_difference: Optional[Decimal] = None,
        metadata_payload: Optional[Dict[str, Any]] = None,
    ) -> ImportBatch:
        """Creates a batch record representing a statement or workbook segment."""
        batch = ImportBatch(
            import_job_id=import_job_id,
            workspace_id=workspace_id,
            source_format=source_format,
            sheet_name=sheet_name,
            row_count=row_count,
            valid_row_count=valid_row_count,
            invalid_row_count=invalid_row_count,
            duplicate_count=duplicate_count,
            column_mapping=column_mapping or {},
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            calculated_closing_balance=calculated_closing_balance,
            reconciliation_difference=reconciliation_difference,
            metadata_payload=metadata_payload or {},
        )
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def get_batch_by_id(
        self,
        workspace_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> Optional[ImportBatch]:
        """Fetches an import batch with its parent job and candidates."""
        stmt = (
            select(ImportBatch)
            .where(
                ImportBatch.id == batch_id,
                ImportBatch.workspace_id == workspace_id,
            )
            .options(
                selectinload(ImportBatch.import_job),
                selectinload(ImportBatch.candidates),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # Import Candidate Operations
    # -----------------------------------------------------------------------

    async def create_candidates_bulk(
        self,
        candidates_data: List[Dict[str, Any]],
    ) -> List[ImportCandidate]:
        """Inserts a collection of candidate rows in batch."""
        candidates: List[ImportCandidate] = []
        for d in candidates_data:
            c = ImportCandidate(
                import_batch_id=d["import_batch_id"],
                workspace_id=d["workspace_id"],
                account_id=d.get("account_id"),
                source_row_number=d["source_row_number"],
                raw_data=d.get("raw_data", {}),
                normalized_data=d.get("normalized_data", {}),
                validation_status=d.get("validation_status", ValidationStatus.VALID.value),
                validation_errors=d.get("validation_errors", []),
                duplicate_status=d.get("duplicate_status", "none"),
                duplicate_match_id=d.get("duplicate_match_id"),
                duplicate_reason=d.get("duplicate_reason"),
                confidence_score=d.get("confidence_score", Decimal("1.00")),
                review_status=d.get("review_status", ReviewStatus.PENDING.value),
                selected_for_import=d.get("selected_for_import", True),
            )
            self.session.add(c)
            candidates.append(c)

        await self.session.flush()
        return candidates

    async def list_candidates(
        self,
        workspace_id: uuid.UUID,
        batch_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        validation_status: Optional[str] = None,
        duplicate_status: Optional[str] = None,
        review_status: Optional[str] = None,
    ) -> Tuple[List[ImportCandidate], int]:
        """Lists candidates for a batch with filters and pagination."""
        base_stmt = select(ImportCandidate).where(
            ImportCandidate.workspace_id == workspace_id,
            ImportCandidate.import_batch_id == batch_id,
        )
        count_stmt = select(func.count()).select_from(ImportCandidate).where(
            ImportCandidate.workspace_id == workspace_id,
            ImportCandidate.import_batch_id == batch_id,
        )

        if validation_status:
            base_stmt = base_stmt.where(ImportCandidate.validation_status == validation_status)
            count_stmt = count_stmt.where(ImportCandidate.validation_status == validation_status)
        if duplicate_status:
            base_stmt = base_stmt.where(ImportCandidate.duplicate_status == duplicate_status)
            count_stmt = count_stmt.where(ImportCandidate.duplicate_status == duplicate_status)
        if review_status:
            base_stmt = base_stmt.where(ImportCandidate.review_status == review_status)
            count_stmt = count_stmt.where(ImportCandidate.review_status == review_status)

        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            base_stmt
            .order_by(ImportCandidate.source_row_number.asc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def get_candidate_by_id(
        self,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> Optional[ImportCandidate]:
        """Fetches a single candidate by ID with workspace isolation."""
        stmt = select(ImportCandidate).where(
            ImportCandidate.id == candidate_id,
            ImportCandidate.workspace_id == workspace_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_selected_valid_candidates(
        self,
        workspace_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> List[ImportCandidate]:
        """Retrieves all candidates marked for confirmation that are valid."""
        stmt = (
            select(ImportCandidate)
            .where(
                ImportCandidate.workspace_id == workspace_id,
                ImportCandidate.import_batch_id == batch_id,
                ImportCandidate.selected_for_import.is_(True),
                ImportCandidate.validation_status == ValidationStatus.VALID.value,
                ImportCandidate.review_status.in_([ReviewStatus.PENDING.value, ReviewStatus.ACCEPTED.value, ReviewStatus.EDITED.value]),
                ImportCandidate.created_transaction_id.is_(None),
            )
            .order_by(ImportCandidate.source_row_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
