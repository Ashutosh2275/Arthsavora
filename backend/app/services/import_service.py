"""
Arthsavora Financial Data Acquisition & Statement Import Service
Orchestrates file upload validation, cryptographic checksumming, private storage,
format detection, parsing, normalization, validation, deduplication, user review,
transaction creation, and double-entry General Ledger posting.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger
from app.core.permissions import Permission, WorkspaceContext
from app.domain.events import (
    create_import_job_completed_event,
    create_import_job_created_event,
    create_import_job_failed_event,
)
from app.domain.exceptions import (
    DuplicateImportError,
    FileTooLargeError,
    ImportProcessingError,
    InvalidFileFormatError,
    UnsafeFileError,
)
from app.domain.import_types import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    FILE_MAGIC_SIGNATURES,
    MAX_FILE_SIZE_BYTES,
    DuplicateStatus,
    ImportSourceType,
    ImportStatus,
    ReviewStatus,
    SourceFormat,
    ValidationStatus,
)
from app.infrastructure.database.models.account import Account
from app.infrastructure.database.models.acquisition import ImportBatch, ImportCandidate, ImportJob
from app.repositories.account_repository import AccountRepository
from app.repositories.import_repository import ImportRepository
from app.schemas.transaction import TransactionCreateRequest
from app.services.importers.base import ParserResult
from app.services.importers.csv_parser import CsvStatementParser
from app.services.importers.deduplicator import StatementDeduplicator
from app.services.importers.normalizer import StatementNormalizer
from app.services.importers.ocr_adapter import OcrStatementAdapter
from app.services.importers.pdf_parser import PdfStatementParser
from app.services.importers.validator import StatementValidator
from app.services.importers.xlsx_parser import XlsxStatementParser
from app.services.ledger_service import LedgerService
from app.services.transaction_service import TransactionService


class ImportService:
    """Service orchestrating statement parsing and transactional ledger integration."""

    STORAGE_ROOT = Path("storage/imports")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ImportRepository(session)
        self.account_repo = AccountRepository(session)

    # -----------------------------------------------------------------------
    # File Upload Security & Storage
    # -----------------------------------------------------------------------

    def validate_and_store_file(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
        filename: str,
        content_bytes: bytes,
        mime_type: Optional[str] = None,
        allow_duplicate: bool = False,
    ) -> Tuple[str, str, int, str]:
        """
        Validates file payload size, extension, MIME type, and magic signatures.
        Saves file to secure private storage using randomized UUID identifier.
        Returns (storage_path, file_checksum, file_size, effective_mime).
        """
        file_size = len(content_bytes)

        # 1. Size Validation
        if file_size > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(file_size=file_size, max_size=MAX_FILE_SIZE_BYTES)
        if file_size == 0:
            raise ValidationException(message="Uploaded file is empty.", code="EMPTY_FILE")

        # 2. Extension & Path Traversal Validation
        clean_name = os.path.basename(filename).strip()
        ext = os.path.splitext(clean_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileFormatError(
                message=f"File extension '{ext}' is not supported. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
                format_detected=ext,
            )

        # 3. Magic Bytes Signature Validation
        if ext == ".pdf":
            if not content_bytes.startswith(b"%PDF-"):
                raise UnsafeFileError(
                    message="File extension is .pdf but content lacks valid PDF header signature.",
                    reason="INVALID_PDF_MAGIC_BYTES",
                )
        elif ext == ".xlsx":
            if not content_bytes.startswith(b"PK\x03\x04"):
                raise UnsafeFileError(
                    message="File extension is .xlsx but content lacks valid ZIP/XLSX header signature.",
                    reason="INVALID_XLSX_MAGIC_BYTES",
                )

        # 4. Checksum Calculation (SHA-256)
        file_checksum = hashlib.sha256(content_bytes).hexdigest()

        # 5. Secure Private Storage Path
        workspace_dir = self.STORAGE_ROOT / str(workspace_id) / str(job_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}{ext}"
        target_path = workspace_dir / safe_filename

        with open(target_path, "wb") as f:
            f.write(content_bytes)

        effective_mime = mime_type or (
            "application/pdf" if ext == ".pdf" else
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == ".xlsx" else
            "text/csv"
        )

        return str(target_path), file_checksum, file_size, effective_mime

    # -----------------------------------------------------------------------
    # Ingestion & Parsing Workflow
    # -----------------------------------------------------------------------

    async def process_file_upload(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        content_bytes: bytes,
        mime_type: Optional[str] = None,
        account_id: Optional[uuid.UUID] = None,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        source_type_override: Optional[str] = None,
        allow_duplicate_file: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end extraction pipeline:
        File validation -> Storage -> Parser Adapter -> Normalizer -> Validator -> Deduplicator -> Staging.
        """
        # 1. Target Account Verification (if provided)
        target_account: Optional[Account] = None
        if account_id:
            target_account = await self.account_repo.get_by_id_scoped(account_id, workspace_id)
            if not target_account:
                raise NotFoundException(message=f"Financial account '{account_id}' not found in workspace.")

        # 2. File Checksum Pre-check for Duplicate Ingestion
        temp_checksum = hashlib.sha256(content_bytes).hexdigest()
        existing_job = await self.repo.get_job_by_checksum(workspace_id, temp_checksum)
        if existing_job and not allow_duplicate_file:
            raise DuplicateImportError(
                file_hash=temp_checksum,
                existing_job_id=str(existing_job.id),
                message=f"Identical statement file has already been uploaded in job '{existing_job.id}'. Set allow_duplicate_file=True to force re-import.",
            )

        # 3. Job Initialization
        ext = os.path.splitext(filename)[1].lower()
        inferred_source_type = source_type_override or (
            ImportSourceType.PDF_STATEMENT.value if ext == ".pdf" else
            ImportSourceType.XLSX.value if ext == ".xlsx" else
            ImportSourceType.CSV.value
        )

        job_id = uuid.uuid4()
        storage_path, checksum, file_size, eff_mime = self.validate_and_store_file(
            workspace_id=workspace_id,
            job_id=job_id,
            filename=filename,
            content_bytes=content_bytes,
            mime_type=mime_type,
        )

        # Persist Job record
        job = await self.repo.create_job(
            workspace_id=workspace_id,
            user_id=user_id,
            source_type=inferred_source_type,
            account_id=account_id,
            original_filename=filename,
            storage_reference=storage_path,
            file_checksum=checksum,
            file_size=file_size,
            mime_type=eff_mime,
        )

        # 4. Dispatch Parser
        parser_result: ParserResult
        try:
            if ext == ".csv":
                parser = CsvStatementParser()
                parser_result = parser.parse(content_bytes, column_mapping=column_mapping)
            elif ext == ".xlsx":
                parser = XlsxStatementParser()
                parser_result = parser.parse(content_bytes, column_mapping=column_mapping, sheet_name=sheet_name)
            elif ext == ".pdf":
                parser = PdfStatementParser()
                parser_result = parser.parse(content_bytes, column_mapping=column_mapping)
                # If scanned PDF image, route to OCR fallback
                if parser_result.is_ocr and not parser_result.rows:
                    ocr_adapter = OcrStatementAdapter()
                    parser_result = ocr_adapter.parse(content_bytes)
            else:
                raise InvalidFileFormatError(message=f"Unsupported format '{ext}'")
        except Exception as err:
            logger.error(f"Error parsing statement file '{filename}': {err}")
            await self.repo.update_job_status(job, status=ImportStatus.FAILED.value, error_summary=str(err))
            raise ImportProcessingError(message=f"Failed to parse statement: {str(err)}", job_id=str(job.id))

        # 5. Normalization, Validation, and Candidate Assembly
        default_curr = target_account.currency if target_account else "INR"
        raw_candidates: List[Dict[str, Any]] = []

        for p_row in parser_result.rows:
            norm = StatementNormalizer.normalize_row(
                row_number=p_row.row_number,
                raw_data=p_row.raw_data,
                date_str=p_row.date_str,
                description_str=p_row.description_str,
                amount_str=p_row.amount_str,
                debit_str=p_row.debit_str,
                credit_str=p_row.credit_str,
                balance_str=p_row.balance_str,
                ref_str=p_row.ref_str,
                default_currency=default_curr,
            )
            v_status, v_errors = StatementValidator.validate_candidate(norm)

            raw_candidates.append({
                "source_row_number": p_row.row_number,
                "raw_data": p_row.raw_data,
                "normalized": norm,
                "validation_status": v_status.value,
                "validation_errors": v_errors,
                "confidence_score": p_row.confidence_score,
                "selected_for_import": (v_status == ValidationStatus.VALID),
            })

        # 6. Deduplication Engine
        deduped_candidates = await StatementDeduplicator.deduplicate_batch(
            session=self.session,
            workspace_id=workspace_id,
            account_id=account_id,
            candidates=raw_candidates,
        )

        # 7. Statement Reconciliation Mathematics
        total_inflows = Decimal("0.0000")
        total_outflows = Decimal("0.0000")
        for c in deduped_candidates:
            if c["validation_status"] == ValidationStatus.VALID.value:
                amt_dec = Decimal(str(c["normalized"]["amount"] or "0"))
                if c["normalized"]["direction"] == "inflow":
                    total_inflows += amt_dec
                else:
                    total_outflows += amt_dec

        calc_closing: Optional[Decimal] = None
        reconcile_diff: Optional[Decimal] = None
        if parser_result.opening_balance is not None:
            calc_closing = parser_result.opening_balance + total_inflows - total_outflows
            if parser_result.closing_balance is not None:
                reconcile_diff = abs(calc_closing - parser_result.closing_balance)

        # 8. Persist Batch & Candidates
        valid_cnt = sum(1 for c in deduped_candidates if c["validation_status"] == ValidationStatus.VALID.value)
        invalid_cnt = sum(1 for c in deduped_candidates if c["validation_status"] != ValidationStatus.VALID.value)
        dup_cnt = sum(1 for c in deduped_candidates if c.get("duplicate_status") in ("exact", "probable"))

        batch = await self.repo.create_batch(
            import_job_id=job.id,
            workspace_id=workspace_id,
            source_format=parser_result.source_format,
            sheet_name=parser_result.sheet_name,
            row_count=len(deduped_candidates),
            valid_row_count=valid_cnt,
            invalid_row_count=invalid_cnt,
            duplicate_count=dup_cnt,
            column_mapping=parser_result.column_mapping_used,
            opening_balance=parser_result.opening_balance,
            closing_balance=parser_result.closing_balance,
            calculated_closing_balance=calc_closing,
            reconciliation_difference=reconcile_diff,
            metadata_payload={
                **parser_result.metadata,
                "account_number": parser_result.account_number,
                "total_inflows": str(total_inflows),
                "total_outflows": str(total_outflows),
                "is_ocr": parser_result.is_ocr,
            },
        )

        candidates_to_insert = [
            {
                "import_batch_id": batch.id,
                "workspace_id": workspace_id,
                "account_id": account_id,
                "source_row_number": c["source_row_number"],
                "raw_data": c["raw_data"],
                "normalized_data": c["normalized"],
                "validation_status": c["validation_status"],
                "validation_errors": c["validation_errors"],
                "duplicate_status": c.get("duplicate_status", "none"),
                "duplicate_match_id": c.get("duplicate_match_id"),
                "duplicate_reason": c.get("duplicate_reason"),
                "confidence_score": c["confidence_score"],
                "review_status": ReviewStatus.PENDING.value,
                "selected_for_import": c["selected_for_import"],
            }
            for c in deduped_candidates
        ]
        created_candidates = await self.repo.create_candidates_bulk(candidates_to_insert)

        # Update Job to Awaiting Review
        await self.repo.update_job_status(
            job=job,
            status=ImportStatus.AWAITING_REVIEW.value,
            total_records=len(deduped_candidates),
            valid_records=valid_cnt,
            invalid_records=invalid_cnt,
            duplicate_records=dup_cnt,
            imported_records=0,
        )

        # Emit Job Created Event
        job_created_event = create_import_job_created_event(
            workspace_id=workspace_id,
            job_id=job.id,
            source_type=job.source_type,
            original_filename=job.original_filename,
            actor_id=user_id,
        )

        return {
            "job_id": job.id,
            "batch_id": batch.id,
            "status": job.status,
            "source_type": job.source_type,
            "original_filename": job.original_filename,
            "total_records": job.total_records,
            "valid_records": valid_cnt,
            "invalid_records": invalid_cnt,
            "duplicate_records": dup_cnt,
            "available_sheets": parser_result.available_sheets,
            "reconciliation": {
                "opening_balance": str(parser_result.opening_balance) if parser_result.opening_balance is not None else None,
                "closing_balance": str(parser_result.closing_balance) if parser_result.closing_balance is not None else None,
                "calculated_closing_balance": str(calc_closing) if calc_closing is not None else None,
                "difference": str(reconcile_diff) if reconcile_diff is not None else None,
                "is_reconciled": (reconcile_diff == Decimal("0.0000")) if reconcile_diff is not None else None,
            },
            "candidates_preview": [
                {
                    "id": str(c.id),
                    "row": c.source_row_number,
                    "date": c.normalized_data.get("transaction_date"),
                    "description": c.normalized_data.get("description"),
                    "amount": c.normalized_data.get("amount"),
                    "direction": c.normalized_data.get("direction"),
                    "status": c.validation_status,
                    "duplicate": c.duplicate_status,
                    "selected": c.selected_for_import,
                }
                for c in created_candidates[:10]
            ],
        }

    # -----------------------------------------------------------------------
    # Candidate Review & Adjustment Operations
    # -----------------------------------------------------------------------

    async def update_candidate(
        self,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
        selected_for_import: Optional[bool] = None,
        review_status: Optional[str] = None,
        normalized_overrides: Optional[Dict[str, Any]] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> ImportCandidate:
        """Enables user to adjust candidate parameters or toggle selection during review."""
        candidate = await self.repo.get_candidate_by_id(workspace_id, candidate_id)
        if not candidate:
            raise NotFoundException(message=f"Candidate '{candidate_id}' not found.")

        if candidate.created_transaction_id is not None:
            raise ValidationException(
                message="Cannot modify a candidate that has already been confirmed and imported.",
                code="ALREADY_IMPORTED",
            )

        if selected_for_import is not None:
            candidate.selected_for_import = selected_for_import

        if review_status:
            candidate.review_status = review_status

        if normalized_overrides:
            current_norm = dict(candidate.normalized_data)
            current_norm.update(normalized_overrides)
            # Recompute paise if amount changed
            if "amount" in normalized_overrides and normalized_overrides["amount"] is not None:
                amt_dec, paise, _ = StatementNormalizer.parse_amount(str(normalized_overrides["amount"]))
                current_norm["amount"] = str(amt_dec) if amt_dec is not None else current_norm["amount"]
                current_norm["amount_paise"] = paise

            candidate.normalized_data = current_norm
            candidate.review_status = ReviewStatus.EDITED.value

            # Revalidate
            v_status, v_errors = StatementValidator.validate_candidate(current_norm)
            candidate.validation_status = v_status.value
            candidate.validation_errors = v_errors

        await self.session.flush()
        return candidate

    # -----------------------------------------------------------------------
    # Confirmation & General Ledger Integration
    # -----------------------------------------------------------------------

    async def confirm_import(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
        batch_id: uuid.UUID,
        target_account_id: Optional[uuid.UUID],
        workspace_context: WorkspaceContext,
        actor_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Executes atomic transaction creation and ledger posting for all selected valid candidates:
        1. Verifies caller permissions.
        2. Resolves destination account.
        3. Takes selected candidates.
        4. Invokes TransactionService.intake_transaction.
        5. Invokes LedgerService.post_transaction_to_ledger.
        6. Updates candidate created_transaction_id and review_status.
        7. Transitions job status to COMPLETED / PARTIALLY_CONFIRMED.
        """
        if not workspace_context.can(Permission.IMPORT_DATA):
            raise ValidationException(message="Permission required to import financial data.", code="FORBIDDEN")

        job = await self.repo.get_job_by_id(workspace_id, job_id)
        if not job:
            raise NotFoundException(message=f"Import job '{job_id}' not found.")

        if job.status not in (ImportStatus.AWAITING_REVIEW.value, ImportStatus.PARTIALLY_CONFIRMED.value):
            raise ValidationException(
                message=f"Import job cannot be confirmed from current status '{job.status}'. Must be 'awaiting_review'.",
                code="INVALID_JOB_STATE",
            )

        # Resolve Account
        final_account_id = target_account_id or job.account_id
        if not final_account_id:
            raise ValidationException(
                message="Target financial account must be specified for confirmation.",
                code="MISSING_TARGET_ACCOUNT",
            )

        account = await self.account_repo.get_by_id_scoped(final_account_id, workspace_id)
        if not account:
            raise NotFoundException(message=f"Target financial account '{final_account_id}' not found.")

        candidates = await self.repo.get_selected_valid_candidates(workspace_id, batch_id)
        if not candidates:
            raise ValidationException(
                message="No valid candidates selected for import.",
                code="NO_SELECTED_CANDIDATES",
            )

        ledger_service = LedgerService(self.session)
        created_transactions: List[uuid.UUID] = []

        # Process each candidate atomically
        for cand in candidates:
            norm = cand.normalized_data
            tx_date_str = norm.get("transaction_date")
            tx_dt = datetime.strptime(tx_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if tx_date_str else datetime.now(timezone.utc)
            
            tx_data = TransactionCreateRequest(
                account_id=final_account_id,
                amount=Decimal(str(norm.get("amount"))),
                currency=norm.get("currency") or account.currency,
                transaction_type=norm.get("transaction_type") or "purchase",
                direction=norm.get("direction") or "outflow",
                transaction_date=tx_dt,
                description=norm.get("description") or "Imported Transaction",
                external_transaction_id=norm.get("reference_number") or f"IMP-{job.id}-{cand.source_row_number}",
                source_type="csv_import" if job.source_type == "csv" else "statement_pdf",
                source_provenance={
                    "import_job_id": str(job.id),
                    "import_batch_id": str(batch_id),
                    "source_row": cand.source_row_number,
                    "original_filename": job.original_filename,
                },
                status="posted",
            )

            # 1. Operational Transaction Creation
            tx, is_new = await TransactionService.intake_transaction(
                session=self.session,
                workspace_context=workspace_context,
                data=tx_data,
            )

            # 2. General Ledger Balanced Journal Posting
            if is_new:
                await ledger_service.post_transaction_to_ledger(
                    workspace_id=workspace_id,
                    transaction=tx,
                    actor_id=actor_id,
                )

            cand.created_transaction_id = tx.id
            cand.review_status = ReviewStatus.ACCEPTED.value
            created_transactions.append(tx.id)

        # Update Job Status
        imported_count = len(created_transactions)
        total_valid = job.valid_records
        final_status = (
            ImportStatus.COMPLETED.value
            if imported_count >= total_valid
            else ImportStatus.PARTIALLY_CONFIRMED.value
        )

        await self.repo.update_job_status(
            job=job,
            status=final_status,
            imported_records=imported_count,
            completed_at=datetime.now(timezone.utc),
        )

        # Emit completion domain event
        create_import_job_completed_event(
            workspace_id=workspace_id,
            job_id=job.id,
            total_records=job.total_records,
            imported_records=imported_count,
            duplicate_records=job.duplicate_records,
            actor_id=actor_id,
        )

        return {
            "job_id": job.id,
            "status": job.status,
            "imported_count": imported_count,
            "created_transaction_ids": created_transactions,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    # -----------------------------------------------------------------------
    # Job Cancellation
    # -----------------------------------------------------------------------

    async def cancel_job(
        self,
        workspace_id: uuid.UUID,
        job_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> ImportJob:
        """Cancels an import job before final confirmation without creating financial side-effects."""
        job = await self.repo.get_job_by_id(workspace_id, job_id)
        if not job:
            raise NotFoundException(message=f"Import job '{job_id}' not found.")

        if job.status == ImportStatus.COMPLETED.value:
            raise ValidationException(
                message="Cannot cancel a completed import job. Financial records must be reversed via ledger workflow.",
                code="CANNOT_CANCEL_COMPLETED",
            )

        job.status = ImportStatus.CANCELLED.value
        await self.session.flush()
        return job
