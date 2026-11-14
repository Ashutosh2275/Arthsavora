"""
Arthsavora Document Intelligence Repository
PostgreSQL persistence for financial documents, OCR extractions, user corrections,
and transaction associations with strict workspace isolation.
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.document import (
    DocumentExtractionResult,
    DocumentReviewRecord,
    DocumentTransactionAssociation,
    FinancialDocument,
)
from app.repositories.workspace_scoped import WorkspaceScopedRepository

logger = logging.getLogger(__name__)


class DocumentRepository(WorkspaceScopedRepository[FinancialDocument]):
    """Manages queries and mutations for tenant-isolated document intelligence entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, FinancialDocument)

    async def create_document(
        self,
        workspace_id: uuid.UUID,
        uploaded_by_id: Optional[uuid.UUID],
        original_filename: str,
        storage_path: str,
        file_size: int,
        mime_type: str,
        file_checksum: str,
        document_type: str = "receipt",
        status: str = "pending",
        preprocessing_metadata: Optional[Dict[str, Any]] = None,
        retention_metadata: Optional[Dict[str, Any]] = None,
    ) -> FinancialDocument:
        """Persists a new uploaded document record."""
        doc = FinancialDocument(
            workspace_id=workspace_id,
            uploaded_by_id=uploaded_by_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            file_checksum=file_checksum,
            document_type=document_type,
            status=status,
            preprocessing_metadata=preprocessing_metadata or {},
            retention_metadata=retention_metadata or {},
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_document_details(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[FinancialDocument]:
        """Loads document with associated extractions, reviews, and transaction links."""
        stmt = (
            select(FinancialDocument)
            .where(
                FinancialDocument.id == document_id,
                FinancialDocument.workspace_id == workspace_id,
            )
            .options(
                selectinload(FinancialDocument.extractions),
                selectinload(FinancialDocument.reviews),
                selectinload(FinancialDocument.transaction_associations).selectinload(
                    DocumentTransactionAssociation.transaction
                ),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_workspace_documents(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FinancialDocument], int]:
        """Lists paginated workspace documents with optional filtering and total count."""
        stmt = select(FinancialDocument).where(FinancialDocument.workspace_id == workspace_id)
        count_stmt = select(func.count()).select_from(FinancialDocument).where(FinancialDocument.workspace_id == workspace_id)

        if status:
            stmt = stmt.where(FinancialDocument.status == status)
            count_stmt = count_stmt.where(FinancialDocument.status == status)

        if document_type:
            stmt = stmt.where(FinancialDocument.document_type == document_type)
            count_stmt = count_stmt.where(FinancialDocument.document_type == document_type)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            stmt = stmt.where(FinancialDocument.original_filename.ilike(pattern))
            count_stmt = count_stmt.where(FinancialDocument.original_filename.ilike(pattern))

        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar_one()

        stmt = (
            stmt.options(
                selectinload(FinancialDocument.extractions),
                selectinload(FinancialDocument.reviews),
                selectinload(FinancialDocument.transaction_associations),
            )
            .order_by(FinancialDocument.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )

        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total_count

    async def update_status(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        status: str,
        preprocessing_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[FinancialDocument]:
        """Updates document processing status and optional preprocessing details."""
        doc = await self.get_by_id_scoped(document_id, workspace_id)
        if not doc:
            return None
        doc.status = status
        if preprocessing_metadata is not None:
            updated_meta = dict(doc.preprocessing_metadata)
            updated_meta.update(preprocessing_metadata)
            doc.preprocessing_metadata = updated_meta
        await self.session.flush()
        return doc

    async def save_extraction_result(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        ocr_provider: str,
        raw_text: str,
        structured_data: Dict[str, Any],
        field_confidences: Dict[str, float],
        overall_confidence: Decimal,
        validation_status: str,
        validation_warnings: List[str],
        ocr_version: Optional[str] = None,
    ) -> DocumentExtractionResult:
        """Persists OCR extraction and parsed entities."""
        extraction = DocumentExtractionResult(
            document_id=document_id,
            workspace_id=workspace_id,
            ocr_provider=ocr_provider,
            ocr_version=ocr_version,
            raw_text=raw_text,
            structured_data=structured_data,
            field_confidences=field_confidences,
            overall_confidence=overall_confidence,
            validation_status=validation_status,
            validation_warnings=validation_warnings,
        )
        self.session.add(extraction)
        await self.session.flush()
        return extraction

    async def get_latest_extraction(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[DocumentExtractionResult]:
        """Retrieves the most recent extraction for a document."""
        stmt = (
            select(DocumentExtractionResult)
            .where(
                DocumentExtractionResult.document_id == document_id,
                DocumentExtractionResult.workspace_id == workspace_id,
            )
            .order_by(DocumentExtractionResult.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def record_review(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        reviewer_id: Optional[uuid.UUID],
        original_data: Dict[str, Any],
        corrected_data: Dict[str, Any],
        review_action: str,
        notes: Optional[str] = None,
    ) -> DocumentReviewRecord:
        """Records an explicit user review or manual correction action."""
        record = DocumentReviewRecord(
            document_id=document_id,
            workspace_id=workspace_id,
            reviewer_id=reviewer_id,
            original_data=original_data,
            corrected_data=corrected_data,
            review_action=review_action,
            notes=notes,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def create_transaction_association(
        self,
        document_id: uuid.UUID,
        transaction_id: uuid.UUID,
        workspace_id: uuid.UUID,
        association_type: str = "created_from_receipt",
        match_score: Optional[Decimal] = None,
        match_evidence: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> DocumentTransactionAssociation:
        """Links document to financial transaction."""
        assoc = DocumentTransactionAssociation(
            document_id=document_id,
            transaction_id=transaction_id,
            workspace_id=workspace_id,
            association_type=association_type,
            match_score=match_score,
            match_evidence=match_evidence or {},
            created_by_id=created_by_id,
        )
        self.session.add(assoc)
        await self.session.flush()
        return assoc

    async def find_by_checksum(
        self,
        workspace_id: uuid.UUID,
        file_checksum: str,
    ) -> Optional[FinancialDocument]:
        """Finds existing document with matching SHA-256 in the workspace for deduplication."""
        stmt = select(FinancialDocument).where(
            FinancialDocument.workspace_id == workspace_id,
            FinancialDocument.file_checksum == file_checksum,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
