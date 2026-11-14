"""
Arthsavora Financial Data Acquisition & Statement Import API Endpoints
RESTful endpoints for statement upload, parsing, candidate review, deduplication,
and General Ledger posting. Supports both workspace-scoped and top-level routing.
"""

import json
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_current_workspace_context
from app.core.exceptions import InsufficientPermissionsException, NotFoundException, ValidationException
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.import_schema import (
    ImportBatchResponse,
    ImportCandidateListResponse,
    ImportCandidateResponse,
    ImportCandidateUpdateRequest,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportJobListResponse,
    ImportJobSummary,
    ImportReconciliationReport,
    ImportUploadResponse,
)
from app.services.import_service import ImportService

router = APIRouter(tags=["Data Acquisition & Imports"])


# ---------------------------------------------------------------------------
# 1. Statement Upload & Ingestion
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=ImportUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a financial statement file (CSV, XLSX, PDF)",
)
async def upload_statement(
    file: UploadFile = File(...),
    account_id: Optional[uuid.UUID] = Form(None),
    column_mapping: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),
    source_type_override: Optional[str] = Form(None),
    allow_duplicate_file: bool = Form(False),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    Accepts multipart file upload, validates cryptographic checksum, enforces file security,
    extracts tabular records, normalizes Indian financial formatting, validates candidate rows,
    and runs multi-level deduplication.
    """
    if not workspace_context.can(Permission.IMPORT_DATA):
        raise InsufficientPermissionsException(message="Permission required to import financial data.")

    parsed_mapping: Optional[Dict[str, str]] = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except Exception:
            raise ValidationException(message="Invalid JSON format in column_mapping field.", code="INVALID_JSON")

    content_bytes = await file.read()
    if not content_bytes:
        raise ValidationException(message="Uploaded file is empty.", code="EMPTY_FILE")

    service = ImportService(session)
    result = await service.process_file_upload(
        workspace_id=workspace_context.workspace.id,
        user_id=current_user.id,
        filename=file.filename or "statement.csv",
        content_bytes=content_bytes,
        mime_type=file.content_type,
        account_id=account_id,
        column_mapping=parsed_mapping,
        sheet_name=sheet_name,
        source_type_override=source_type_override,
        allow_duplicate_file=allow_duplicate_file,
    )
    return result


# ---------------------------------------------------------------------------
# 2. List & Inspect Import Jobs
# ---------------------------------------------------------------------------

@router.get(
    "/jobs",
    response_model=ImportJobListResponse,
    summary="List all import jobs for the workspace",
)
async def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Lists historical and active import jobs with paginated telemetry."""
    if not workspace_context.can(Permission.VIEW_IMPORTS):
        raise InsufficientPermissionsException(message="Permission required to view import jobs.")

    service = ImportService(session)
    items, total = await service.repo.list_jobs(
        workspace_id=workspace_context.workspace.id,
        limit=limit,
        offset=offset,
        status=status,
        source_type=source_type,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/jobs/{job_id}",
    response_model=ImportJobSummary,
    summary="Get single import job details",
)
async def get_import_job(
    job_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Retrieves an import job by ID."""
    if not workspace_context.can(Permission.VIEW_IMPORTS):
        raise InsufficientPermissionsException(message="Permission required to view import jobs.")

    service = ImportService(session)
    job = await service.repo.get_job_by_id(workspace_context.workspace.id, job_id)
    if not job:
        raise NotFoundException(message=f"Import job '{job_id}' not found.")
    return job


# ---------------------------------------------------------------------------
# 3. Candidate Review Operations
# ---------------------------------------------------------------------------

@router.get(
    "/batches/{batch_id}/candidates",
    response_model=ImportCandidateListResponse,
    summary="List candidate transactions in a batch for review",
)
async def list_batch_candidates(
    batch_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    validation_status: Optional[str] = Query(None),
    duplicate_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Fetches candidate transaction rows with validation status, duplicate hints, and confidence scores."""
    if not workspace_context.can(Permission.VIEW_IMPORTS):
        raise InsufficientPermissionsException(message="Permission required to inspect import candidates.")

    service = ImportService(session)
    items, total = await service.repo.list_candidates(
        workspace_id=workspace_context.workspace.id,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
        validation_status=validation_status,
        duplicate_status=duplicate_status,
        review_status=review_status,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch(
    "/candidates/{candidate_id}",
    response_model=ImportCandidateResponse,
    summary="Update candidate review decision, selection, or values",
)
async def update_candidate(
    candidate_id: uuid.UUID,
    body: ImportCandidateUpdateRequest,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Modifies user review flags, toggles import inclusion, or updates candidate fields."""
    if not workspace_context.can(Permission.IMPORT_DATA):
        raise InsufficientPermissionsException(message="Permission required to edit import candidates.")

    service = ImportService(session)
    overrides: Dict[str, Any] = {}
    if body.description is not None:
        overrides["description"] = body.description
    if body.transaction_date is not None:
        overrides["transaction_date"] = body.transaction_date
    if body.amount is not None:
        overrides["amount"] = str(body.amount)
    if body.direction is not None:
        overrides["direction"] = body.direction
    if body.transaction_type is not None:
        overrides["transaction_type"] = body.transaction_type
    if body.category_id is not None:
        overrides["category_id"] = str(body.category_id)

    candidate = await service.update_candidate(
        workspace_id=workspace_context.workspace.id,
        candidate_id=candidate_id,
        selected_for_import=body.selected_for_import,
        review_status=body.review_status,
        normalized_overrides=overrides if overrides else None,
        actor_id=current_user.id,
    )
    return candidate


# ---------------------------------------------------------------------------
# 4. Confirmation & Ledger Posting
# ---------------------------------------------------------------------------

@router.post(
    "/jobs/{job_id}/batches/{batch_id}/confirm",
    response_model=ImportConfirmResponse,
    summary="Confirm review and create financial transactions with ledger entries",
)
async def confirm_batch_import(
    job_id: uuid.UUID,
    batch_id: uuid.UUID,
    body: ImportConfirmRequest,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    Finalizes import:
    Creates operational transactions through TransactionService and posts
    balanced general ledger journal entries through LedgerService.
    """
    if not workspace_context.can(Permission.IMPORT_DATA):
        raise InsufficientPermissionsException(message="Permission required to confirm import.")

    service = ImportService(session)
    result = await service.confirm_import(
        workspace_id=workspace_context.workspace.id,
        job_id=job_id,
        batch_id=batch_id,
        target_account_id=body.target_account_id,
        workspace_context=workspace_context,
        actor_id=current_user.id,
    )
    return result


# ---------------------------------------------------------------------------
# 5. Cancellation & Reconciliation
# ---------------------------------------------------------------------------

@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ImportJobSummary,
    summary="Cancel an unconfirmed import job",
)
async def cancel_import_job(
    job_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Cancels an import job before confirmation."""
    if not workspace_context.can(Permission.IMPORT_DATA):
        raise InsufficientPermissionsException(message="Permission required to cancel import.")

    service = ImportService(session)
    job = await service.cancel_job(workspace_context.workspace.id, job_id, current_user.id)
    return job


@router.get(
    "/batches/{batch_id}/reconciliation",
    response_model=ImportReconciliationReport,
    summary="Get statement balance reconciliation report",
)
async def get_statement_reconciliation(
    batch_id: uuid.UUID,
    workspace_context: WorkspaceContext = Depends(get_current_workspace_context),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Returns reconciliation comparison between statement opening/closing balances and transactions."""
    if not workspace_context.can(Permission.VIEW_IMPORTS):
        raise InsufficientPermissionsException(message="Permission required to view statement reconciliation.")

    service = ImportService(session)
    batch = await service.repo.get_batch_by_id(workspace_context.workspace.id, batch_id)
    if not batch:
        raise NotFoundException(message=f"Batch '{batch_id}' not found.")

    meta = batch.metadata_payload or {}
    inflows = Decimal(str(meta.get("total_inflows", "0.0000")))
    outflows = Decimal(str(meta.get("total_outflows", "0.0000")))

    is_reconciled = False
    if batch.reconciliation_difference is not None:
        is_reconciled = (batch.reconciliation_difference == Decimal("0.0000"))

    return {
        "batch_id": batch.id,
        "opening_balance": batch.opening_balance,
        "closing_balance": batch.closing_balance,
        "total_inflows": inflows,
        "total_outflows": outflows,
        "calculated_closing_balance": batch.calculated_closing_balance,
        "difference": batch.reconciliation_difference,
        "is_reconciled": is_reconciled,
        "details": meta,
    }
