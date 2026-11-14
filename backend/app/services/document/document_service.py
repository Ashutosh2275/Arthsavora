"""
Arthsavora Document Intelligence Application Service
Orchestrates secure document upload, image preprocessing, multi-provider OCR extraction,
entity parsing, Indian GST validation, merchant enrichment, transaction matching,
user corrections, and explicit confirmation before authoritative ledger posting.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import Permission, WorkspaceContext
from app.domain.document import (
    DocumentStatus,
    DocumentType,
    PaymentMethod,
    StructuredReceiptDataVO,
    TransactionMatchStatus,
    ValidationStatus,
    parse_indian_date,
)
from app.domain.money import Money
from app.infrastructure.database.models.document import (
    DocumentExtractionResult,
    DocumentReviewRecord,
    DocumentTransactionAssociation,
    FinancialDocument,
)
from app.infrastructure.database.models.transaction import Transaction
from app.repositories.document_repository import DocumentRepository
from app.schemas.transaction import TransactionCreateRequest
from app.services.document.enrichment import DocumentEnricher
from app.services.document.field_extractor import ReceiptFieldExtractor
from app.services.document.matcher import TransactionMatchCandidate, TransactionMatcher
from app.services.document.ocr.factory import get_ocr_engine
from app.services.document.preprocessor import ImagePreprocessor
from app.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

# Max file size limit: 15 MB
MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # And WEBP at offset 8
    "application/pdf": [b"%PDF-"],
}


class DocumentService:
    """Core application service managing the lifecycle of financial documents and OCR intelligence."""

    STORAGE_ROOT = Path("storage/documents")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DocumentRepository(session)
        self.enricher = DocumentEnricher(session)
        self.matcher = TransactionMatcher(session)

    @classmethod
    def validate_file_bytes(cls, content: bytes, original_filename: str) -> str:
        """
        Validates document file size, magic bytes, and returns verified MIME type.
        Raises ValidationException if file is invalid or insecure.
        """
        if len(content) == 0:
            raise ValidationException(message="Uploaded file is empty.", code="FILE_EMPTY")

        if len(content) > MAX_DOCUMENT_SIZE_BYTES:
            max_mb = MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)
            raise ValidationException(
                message=f"File exceeds maximum allowed size of {max_mb} MB.",
                code="FILE_TOO_LARGE",
            )

        # Magic byte signature detection
        detected_mime = None
        if content.startswith(b"%PDF-"):
            detected_mime = "application/pdf"
        elif content.startswith(b"\xFF\xD8\xFF"):
            detected_mime = "image/jpeg"
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):
            detected_mime = "image/png"
        elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            detected_mime = "image/webp"

        if not detected_mime:
            raise ValidationException(
                message=(
                    "Unsupported or invalid document format. Only verified PDF, "
                    "JPEG, PNG, and WebP files are permitted."
                ),
                code="UNSUPPORTED_DOCUMENT_FORMAT",
            )

        return detected_mime

    async def upload_document(
        self,
        workspace_context: WorkspaceContext,
        file_bytes: bytes,
        original_filename: str,
        document_type: str = "receipt",
        auto_process: bool = True,
        ocr_provider: Optional[str] = None,
    ) -> FinancialDocument:
        """
        Uploads and persists a financial document under strict workspace isolation.
        Automatically kicks off OCR processing when auto_process=True.
        """
        if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
            raise ForbiddenException(message="Permission required to upload financial documents.")

        ws_id = workspace_context.workspace.id
        user_id = workspace_context.user.id

        # 1. Validate magic bytes and format
        mime_type = self.validate_file_bytes(file_bytes, original_filename)

        # 2. Checksum for integrity and deduplication
        checksum = hashlib.sha256(file_bytes).hexdigest()

        # Check for existing document with same checksum
        existing = await self.repo.find_by_checksum(ws_id, checksum)
        if existing and existing.status != DocumentStatus.REJECTED.value:
            logger.info(f"Existing document {existing.id} found for checksum {checksum}")
            # If already processed, return existing
            return existing

        doc_id = uuid.uuid4()
        ext = Path(original_filename).suffix.lower() or (".pdf" if mime_type == "application/pdf" else ".png")
        stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(original_filename).stem) or "original"
        target_dir = self.STORAGE_ROOT / str(ws_id) / str(doc_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        stored_file_path = target_dir / f"{stem}{ext}"
        with open(stored_file_path, "wb") as f:
            f.write(file_bytes)

        # 3. Create database record
        doc = await self.repo.create_document(
            workspace_id=ws_id,
            uploaded_by_id=user_id,
            original_filename=original_filename,
            storage_path=str(stored_file_path),
            file_size=len(file_bytes),
            mime_type=mime_type,
            file_checksum=checksum,
            document_type=document_type,
            status=DocumentStatus.PENDING.value,
            preprocessing_metadata={},
            retention_metadata={
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "original_filename": original_filename,
            },
        )

        if auto_process:
            return await self.process_document(
                workspace_context=workspace_context,
                document_id=doc.id,
                ocr_provider=ocr_provider,
            )

        return doc

    async def process_document(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
        ocr_provider: Optional[str] = None,
    ) -> FinancialDocument:
        """
        Executes preprocessing, OCR, entity extraction, mathematical validation, and enrichment.
        """
        if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
            raise ForbiddenException(message="Permission required to process documents.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_by_id_scoped(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        try:
            # 1. Preprocessing phase (if image)
            preprocessed_path = doc.storage_path
            preprocessing_meta: Dict[str, Any] = {}

            if doc.mime_type in ("image/jpeg", "image/png", "image/webp"):
                await self.repo.update_status(doc.id, ws_id, DocumentStatus.PREPROCESSING.value)
                preprocessed_path, preprocessing_meta = ImagePreprocessor.preprocess_image(
                    doc.storage_path
                )
                await self.repo.update_status(
                    doc.id,
                    ws_id,
                    DocumentStatus.PROCESSING.value,
                    preprocessing_metadata=preprocessing_meta,
                )
            else:
                await self.repo.update_status(doc.id, ws_id, DocumentStatus.PROCESSING.value)

            # 2. OCR text extraction
            engine = get_ocr_engine(provider=ocr_provider, mime_type=doc.mime_type)
            ocr_result = await engine.extract_text(preprocessed_path, mime_type=doc.mime_type)

            # 3. Entity extraction & mathematical validation
            (
                structured_vo,
                field_confs,
                overall_conf,
                val_status,
                val_warnings,
            ) = ReceiptFieldExtractor.extract_structured_data(ocr_result.text)

            # 4. Merchant & Category Enrichment
            enriched_vo = await self.enricher.enrich_receipt_data(ws_id, structured_vo)

            # 5. Persist extraction result
            await self.repo.save_extraction_result(
                document_id=doc.id,
                workspace_id=ws_id,
                ocr_provider=ocr_result.provider,
                ocr_version=ocr_result.version,
                raw_text=ocr_result.text,
                structured_data=enriched_vo.to_dict(),
                field_confidences=field_confs,
                overall_confidence=overall_conf,
                validation_status=val_status.value,
                validation_warnings=val_warnings,
            )

            # 6. Update document status
            # If confidence is below 0.70 or arithmetic has warnings, set review_required
            final_status = (
                DocumentStatus.REVIEW_REQUIRED.value
                if (overall_conf < Decimal("0.70") or val_status != ValidationStatus.VALID)
                else DocumentStatus.EXTRACTED.value
            )
            await self.repo.update_status(doc.id, ws_id, final_status)

            return await self.repo.get_document_details(doc.id, ws_id) or doc

        except Exception as e:
            logger.error(f"Processing failed for document {document_id}: {e}", exc_info=True)
            await self.repo.update_status(
                doc.id,
                ws_id,
                DocumentStatus.FAILED.value,
                preprocessing_metadata={"error": str(e)},
            )
            raise

    async def correct_extraction(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
        corrected_data: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> FinancialDocument:
        """
        Applies user field corrections to an extracted document.
        Does NOT post to ledger; updates extraction record with human-confirmed data.
        """
        if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
            raise ForbiddenException(message="Permission required to update document extraction.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_document_details(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        latest_extraction = await self.repo.get_latest_extraction(document_id, ws_id)
        original_data = latest_extraction.structured_data if latest_extraction else {}

        # Merge corrected fields into structured data
        merged_data = dict(original_data)
        merged_data.update(corrected_data)

        # Reconstruct VO and re-validate math
        structured_vo = StructuredReceiptDataVO.from_dict(merged_data)

        # Update monetary paise fields if amounts changed
        if "total_amount" in corrected_data:
            dec, paise = Money.from_amount(str(corrected_data["total_amount"]), structured_vo.currency).amount, Money.from_amount(str(corrected_data["total_amount"]), structured_vo.currency).minor_units
            structured_vo.total_amount = dec
            structured_vo.total_amount_paise = paise

        if "subtotal" in corrected_data:
            dec, paise = Money.from_amount(str(corrected_data["subtotal"]), structured_vo.currency).amount, Money.from_amount(str(corrected_data["subtotal"]), structured_vo.currency).minor_units
            structured_vo.subtotal = dec
            structured_vo.subtotal_paise = paise

        val_status, val_warnings = ReceiptFieldExtractor._extract_subtotal("", [])[0], []
        # Run receipt validation
        from app.domain.document import validate_receipt_math
        val_status, val_warnings = validate_receipt_math(
            subtotal_paise=structured_vo.subtotal_paise,
            total_tax_paise=structured_vo.taxes.total_tax_paise,
            discount_paise=structured_vo.discount_paise,
            total_amount_paise=structured_vo.total_amount_paise,
            line_items=structured_vo.line_items,
        )

        # Persist new extraction reflecting the manual correction
        new_ext = await self.repo.save_extraction_result(
            document_id=doc.id,
            workspace_id=ws_id,
            ocr_provider="user_correction",
            raw_text=latest_extraction.raw_text if latest_extraction else "",
            structured_data=structured_vo.to_dict(),
            field_confidences={k: 1.0 for k in structured_vo.to_dict().keys()},
            overall_confidence=Decimal("1.0000"),
            validation_status=val_status.value,
            validation_warnings=val_warnings,
        )

        # Record review audit trail
        review_record = await self.repo.record_review(
            document_id=doc.id,
            workspace_id=ws_id,
            reviewer_id=workspace_context.user.id,
            original_data=original_data,
            corrected_data=structured_vo.to_dict(),
            review_action="edited",
            notes=notes,
        )

        await self.repo.update_status(doc.id, ws_id, DocumentStatus.EXTRACTED.value)

        # Ensure latest items are at the front of collections
        existing_exts = [e for e in doc.extractions if e.id != new_ext.id]
        doc.extractions = [new_ext] + existing_exts
        existing_revs = [r for r in doc.reviews if r.id != review_record.id]
        doc.reviews = [review_record] + existing_revs

        return doc

    async def confirm_and_create_transaction(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
        account_id: uuid.UUID,
        confirmed_data: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Transaction, DocumentTransactionAssociation]:
        """
        Explicit user confirmation gate:
        Transforms verified receipt information into an authoritative financial transaction.
        Enforces double-entry or operational invariants, updates account balance,
        and creates a persistent association between document and transaction.
        """
        if not workspace_context.can(Permission.CREATE_TRANSACTIONS):
            raise ForbiddenException(message="Permission required to create financial transactions.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_document_details(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        if doc.status == DocumentStatus.CONFIRMED.value and doc.transaction_associations:
            raise BusinessRuleViolationException(
                message="This document has already been confirmed and linked to a transaction."
            )

        latest_extraction = await self.repo.get_latest_extraction(document_id, ws_id)
        if not latest_extraction:
            raise ValidationException(
                message="Cannot confirm a document with no extraction data.",
                code="NO_EXTRACTION_DATA",
            )

        data = dict(latest_extraction.structured_data)
        if confirmed_data:
            data.update(confirmed_data)

        vo = StructuredReceiptDataVO.from_dict(data)
        if vo.total_amount_paise <= 0:
            raise ValidationException(
                message="Cannot create transaction: Total amount must be positive.",
                code="INVALID_AMOUNT",
            )

        # Parse transaction date
        txn_date = parse_indian_date(vo.receipt_date) if vo.receipt_date else None
        if not txn_date:
            txn_date = date.today()

        category_uuid = None
        if vo.suggested_category_id:
            try:
                category_uuid = uuid.UUID(vo.suggested_category_id)
            except ValueError:
                pass

        description = vo.merchant_name or doc.original_filename
        if vo.invoice_number:
            description += f" (Bill #{vo.invoice_number})"

        # Build TransactionCreateRequest
        tx_req = TransactionCreateRequest(
            account_id=account_id,
            amount=str(vo.total_amount),
            currency=vo.currency or "INR",
            transaction_type="expense",
            direction="outflow",
            transaction_date=txn_date,
            description=description,
            merchant_name=vo.merchant_name,
            category_id=category_uuid,
            status="posted",
            source_type="ocr",
            source_reference=str(doc.id),
            external_transaction_id=vo.payment_reference,
            is_ai_predicted=False,
            metadata={
                "document_id": str(doc.id),
                "invoice_number": vo.invoice_number,
                "gstin": vo.gstin,
                "notes": notes,
            },
        )

        # Create authoritative transaction
        tx, _ = await TransactionService.intake_transaction(
            session=self.session,
            workspace_context=workspace_context,
            data=tx_req,
        )

        # Create association
        assoc = await self.repo.create_transaction_association(
            document_id=doc.id,
            transaction_id=tx.id,
            workspace_id=ws_id,
            association_type="created_from_receipt",
            match_score=Decimal("1.0000"),
            match_evidence={
                "confirmed_by_user": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            created_by_id=workspace_context.user.id,
        )

        # Record review audit
        await self.repo.record_review(
            document_id=doc.id,
            workspace_id=ws_id,
            reviewer_id=workspace_context.user.id,
            original_data=latest_extraction.structured_data,
            corrected_data=vo.to_dict(),
            review_action="confirmed",
            notes=notes,
        )

        # Mark document confirmed
        await self.repo.update_status(doc.id, ws_id, DocumentStatus.CONFIRMED.value)

        return tx, assoc

    async def match_and_associate(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
        transaction_id: uuid.UUID,
        match_score: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> DocumentTransactionAssociation:
        """
        Associates an existing financial transaction with this document as supporting documentation.
        """
        if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
            raise ForbiddenException(message="Permission required to link documents to transactions.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_by_id_scoped(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        # Verify target transaction exists in same workspace
        tx_repo = TransactionService
        tx = await TransactionService.get_transaction(self.session, workspace_context, transaction_id)
        if not tx:
            raise NotFoundException(message="Target transaction not found in workspace.")

        assoc = await self.repo.create_transaction_association(
            document_id=doc.id,
            transaction_id=tx.id,
            workspace_id=ws_id,
            association_type="matched_existing",
            match_score=match_score or Decimal("1.0000"),
            match_evidence={
                "user_confirmed": True,
                "linked_at": datetime.now(timezone.utc).isoformat(),
                "notes": notes,
            },
            created_by_id=workspace_context.user.id,
        )

        await self.repo.update_status(doc.id, ws_id, DocumentStatus.CONFIRMED.value)
        return assoc

    async def reject_document(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> FinancialDocument:
        """Marks document as rejected by user with audit notes."""
        if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
            raise ForbiddenException(message="Permission required to reject documents.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_by_id_scoped(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        latest_extraction = await self.repo.get_latest_extraction(document_id, ws_id)
        original_data = latest_extraction.structured_data if latest_extraction else {}

        await self.repo.record_review(
            document_id=doc.id,
            workspace_id=ws_id,
            reviewer_id=workspace_context.user.id,
            original_data=original_data,
            corrected_data={},
            review_action="rejected",
            notes=notes,
        )

        await self.repo.update_status(doc.id, ws_id, DocumentStatus.REJECTED.value)
        return await self.repo.get_document_details(doc.id, ws_id) or doc

    async def find_transaction_matches(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
    ) -> List[TransactionMatchCandidate]:
        """Runs match scan between extracted document data and existing transactions."""
        if not workspace_context.can(Permission.VIEW_DOCUMENTS):
            raise ForbiddenException(message="Permission required to view document matches.")

        ws_id = workspace_context.workspace.id
        latest = await self.repo.get_latest_extraction(document_id, ws_id)
        if not latest:
            return []

        vo = StructuredReceiptDataVO.from_dict(latest.structured_data)
        return await self.matcher.find_matches(workspace_id=ws_id, receipt=vo)

    async def get_document_file_path(
        self,
        workspace_context: WorkspaceContext,
        document_id: uuid.UUID,
    ) -> Tuple[str, str, str]:
        """Returns (storage_path, original_filename, mime_type) for download or inline preview."""
        if not workspace_context.can(Permission.VIEW_DOCUMENTS):
            raise ForbiddenException(message="Permission required to view documents.")

        ws_id = workspace_context.workspace.id
        doc = await self.repo.get_by_id_scoped(document_id, ws_id)
        if not doc:
            raise NotFoundException(message="Financial document not found.")

        if not os.path.exists(doc.storage_path):
            raise NotFoundException(message="Document physical file missing from storage.")

        return doc.storage_path, doc.original_filename, doc.mime_type
