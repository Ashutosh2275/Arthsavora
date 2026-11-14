"""
Arthsavora Document Intelligence & Receipt Processing API Endpoints
RESTful endpoints for secure receipt/invoice upload, image preprocessing, OCR extraction,
entity field corrections, transaction matching, and explicit confirmation before ledger creation.
"""

from decimal import Decimal
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_workspace_context
from app.core.exceptions import NotFoundException
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.document_schema import (
    DocumentConfirmRequest,
    DocumentCorrectionRequest,
    DocumentExtractionResponse,
    DocumentListResponse,
    DocumentMatchAssociateRequest,
    DocumentTransactionAssociationResponse,
    FinancialDocumentResponse,
    TransactionMatchCandidateResponse,
)
from app.services.document.document_service import DocumentService
from app.services.transaction_service import TransactionService

router = APIRouter(tags=["Receipt Intelligence & Documents"])


@router.post(
    "/upload",
    response_model=FinancialDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a financial receipt or invoice",
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("receipt"),
    auto_process: bool = Form(True),
    ocr_provider: Optional[str] = Form(None),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Uploads a receipt image (JPEG, PNG, WebP) or invoice document (PDF).
    Verifies magic bytes, calculates SHA-256 checksum, and initiates OCR processing pipeline.
    """
    file_bytes = await file.read()
    service = DocumentService(session)
    doc = await service.upload_document(
        workspace_context=workspace_context,
        file_bytes=file_bytes,
        original_filename=file.filename or "receipt.png",
        document_type=document_type,
        auto_process=auto_process,
        ocr_provider=ocr_provider,
    )
    return doc


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List workspace documents with filters and pagination",
)
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    document_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves paginated list of documents under current workspace tenant."""
    if not workspace_context.can(Permission.VIEW_DOCUMENTS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required to view documents.",
        )

    service = DocumentService(session)
    docs, total = await service.repo.list_workspace_documents(
        workspace_id=workspace_context.workspace.id,
        status=status_filter,
        document_type=document_type,
        search_query=search,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(items=docs, total=total, limit=limit, offset=offset)


@router.get(
    "/{document_id}",
    response_model=FinancialDocumentResponse,
    summary="Retrieve document metadata and extraction details",
)
async def get_document(
    document_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves a single financial document with extraction history and associations."""
    if not workspace_context.can(Permission.VIEW_DOCUMENTS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required to view documents.",
        )

    service = DocumentService(session)
    doc = await service.repo.get_document_details(document_id, workspace_context.workspace.id)
    if not doc:
        raise NotFoundException(message="Document not found.")
    return doc


@router.get(
    "/{document_id}/download",
    summary="Download or stream original receipt/document file",
)
async def download_document(
    document_id: uuid.UUID,
    preview: bool = Query(False, description="Whether to display inline preview or trigger attachment download"),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Streams original document file content with security header protection."""
    service = DocumentService(session)
    file_path, filename, mime_type = await service.get_document_file_path(
        workspace_context=workspace_context,
        document_id=document_id,
    )

    disposition = "inline" if preview else f'attachment; filename="{filename}"'
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers={"Content-Disposition": disposition},
    )


@router.get(
    "/{document_id}/extraction",
    response_model=DocumentExtractionResponse,
    summary="Get latest OCR extraction result for document",
)
async def get_latest_extraction(
    document_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Fetches the latest structured extraction data and confidence metrics."""
    if not workspace_context.can(Permission.VIEW_DOCUMENTS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required to view extraction.",
        )

    service = DocumentService(session)
    ext = await service.repo.get_latest_extraction(document_id, workspace_context.workspace.id)
    if not ext:
        raise NotFoundException(message="No extraction result found for this document.")
    return ext


@router.post(
    "/{document_id}/process",
    response_model=FinancialDocumentResponse,
    summary="Trigger or re-run OCR extraction for a document",
)
async def process_document(
    document_id: uuid.UUID,
    ocr_provider: Optional[str] = Query(None),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Triggers image preprocessing, OCR execution, entity extraction, and enrichment."""
    service = DocumentService(session)
    return await service.process_document(
        workspace_context=workspace_context,
        document_id=document_id,
        ocr_provider=ocr_provider,
    )


@router.patch(
    "/{document_id}/extraction",
    response_model=FinancialDocumentResponse,
    summary="Submit user corrections to extracted receipt entities",
)
async def correct_extraction(
    document_id: uuid.UUID,
    request: DocumentCorrectionRequest,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Updates extracted values with human-confirmed corrections and audit notes."""
    service = DocumentService(session)
    return await service.correct_extraction(
        workspace_context=workspace_context,
        document_id=document_id,
        corrected_data=request.corrected_data,
        notes=request.notes,
    )


@router.post(
    "/{document_id}/confirm",
    status_code=status.HTTP_201_CREATED,
    summary="Explicitly confirm receipt data and create an authoritative financial transaction",
)
async def confirm_and_create_transaction(
    document_id: uuid.UUID,
    request: DocumentConfirmRequest,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Explicit user confirmation gate:
    Mutates account balance and creates an authoritative financial transaction
    linked to the supporting document.
    """
    service = DocumentService(session)
    tx, assoc = await service.confirm_and_create_transaction(
        workspace_context=workspace_context,
        document_id=document_id,
        account_id=request.account_id,
        confirmed_data=request.confirmed_data,
        notes=request.notes,
    )

    return {
        "status": "confirmed",
        "transaction": TransactionService.format_transaction_response(tx),
        "association": DocumentTransactionAssociationResponse.model_validate(assoc),
    }


@router.post(
    "/{document_id}/match",
    response_model=List[TransactionMatchCandidateResponse],
    summary="Scan workspace for transactions matching receipt amount and date",
)
async def find_matching_transactions(
    document_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Identifies potential matching transactions in the workspace with evidence scores."""
    service = DocumentService(session)
    candidates = await service.find_transaction_matches(
        workspace_context=workspace_context,
        document_id=document_id,
    )
    return [
        TransactionMatchCandidateResponse(
            transaction_id=c.transaction_id,
            match_status=c.match_status.value,
            match_score=c.match_score,
            evidence=c.evidence,
            transaction_summary=c.transaction_summary,
        )
        for c in candidates
    ]


@router.post(
    "/{document_id}/associate",
    response_model=DocumentTransactionAssociationResponse,
    summary="Associate receipt with an existing financial transaction",
)
async def associate_with_existing_transaction(
    document_id: uuid.UUID,
    request: DocumentMatchAssociateRequest,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Links document to an existing transaction as supporting documentation."""
    service = DocumentService(session)
    assoc = await service.match_and_associate(
        workspace_context=workspace_context,
        document_id=document_id,
        transaction_id=request.transaction_id,
        match_score=request.match_score,
        notes=request.notes,
    )
    return assoc


@router.post(
    "/{document_id}/reject",
    response_model=FinancialDocumentResponse,
    summary="Reject an unverified or invalid receipt",
)
async def reject_document(
    document_id: uuid.UUID,
    notes: Optional[str] = Query(None),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Marks document as rejected with audit record."""
    service = DocumentService(session)
    return await service.reject_document(
        workspace_context=workspace_context,
        document_id=document_id,
        notes=notes,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a financial document",
)
async def delete_document(
    document_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    session: AsyncSession = Depends(get_db_session),
):
    """Permanently deletes document file and database record."""
    if not workspace_context.can(Permission.MANAGE_DOCUMENTS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required to delete documents.",
        )

    service = DocumentService(session)
    ws_id = workspace_context.workspace.id
    doc = await service.repo.get_by_id_scoped(document_id, ws_id)
    if not doc:
        raise NotFoundException(message="Document not found.")

    if os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
            doc_folder = Path(doc.storage_path).parent
            if doc_folder.exists() and not any(doc_folder.iterdir()):
                doc_folder.rmdir()
        except Exception as e:
            logger.warning(f"Error deleting physical file: {e}")

    await service.repo.delete(doc)
    return None
