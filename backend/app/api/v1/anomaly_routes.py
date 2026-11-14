"""
Arthsavora Financial Anomaly Detection, Fraud Signals & Risk Intelligence API Endpoints
Authenticated, workspace-scoped RESTful routes for anomaly inspection, user review decisions,
customizable detection rules, whitelist exceptions, risk summaries, and trends.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.common import ApiResponse
from app.schemas.anomaly_schema import (
    AnomalyDetectionResponse,
    AnomalyReviewRequest,
    AnomalyScanRequest,
    AnomalySummaryResponse,
    AnomalyTrendsResponse,
    DetectionExceptionCreateRequest,
    DetectionExceptionResponse,
    DetectionRuleResponse,
    DetectionRuleUpdateRequest,
)
from app.services.anomaly.detection_service import AnomalyDetectionService
from app.services.anomaly.review_service import AnomalyReviewService
from app.repositories.anomaly_repository import AnomalyRepository

router = APIRouter(tags=["Financial Anomaly Detection, Fraud Signals & Risk Intelligence"])


# -------------------------------------------------------------------------
# Anomaly Queries & Scans
# -------------------------------------------------------------------------

@router.get(
    "",
    response_model=ApiResponse[List[AnomalyDetectionResponse]],
    summary="List Detected Anomalies",
    description="Retrieves workspace anomalies with optional filtering by status, severity, and detection type.",
)
async def list_anomalies(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    detection_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[AnomalyDetectionResponse]]:
    repo = AnomalyRepository(db)
    items, total = await repo.list_detections(
        workspace_id=context.workspace_id,
        status=status_filter,
        severity=severity,
        detection_type=detection_type,
        limit=limit,
        offset=offset,
    )
    dtos = [AnomalyDetectionService.map_to_dto(item) for item in items]
    return ApiResponse(
        data=dtos,
        message=f"Retrieved {len(dtos)} of {total} anomaly detections.",
    )


@router.get(
    "/summary",
    response_model=ApiResponse[AnomalySummaryResponse],
    summary="Get Security Risk Overview",
    description="Returns aggregate counts of open, high-severity, and resolved anomalies with average risk score.",
)
async def get_anomaly_summary(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalySummaryResponse]:
    repo = AnomalyRepository(db)
    summary_data = await repo.get_summary(context.workspace_id)
    return ApiResponse(
        data=AnomalySummaryResponse(**summary_data),
        message="Anomaly summary retrieved successfully.",
    )


@router.get(
    "/trends",
    response_model=ApiResponse[AnomalyTrendsResponse],
    summary="Get Anomaly Risk Trends",
    description="Returns daily historical anomaly counts broken down by severity.",
)
async def get_anomaly_trends(
    lookback_days: int = Query(30, ge=7, le=90),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalyTrendsResponse]:
    repo = AnomalyRepository(db)
    trends = await repo.get_trends(context.workspace_id, lookback_days=lookback_days)
    return ApiResponse(
        data=AnomalyTrendsResponse(
            workspace_id=context.workspace_id,
            lookback_days=lookback_days,
            trends=trends,
        ),
        message=f"Anomaly trends for past {lookback_days} days retrieved.",
    )


@router.post(
    "/scan",
    response_model=ApiResponse[List[AnomalyDetectionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Scan Recent Transactions",
    description="Executes anomaly detection across recent posted transactions in the workspace.",
)
async def scan_recent_transactions(
    request: AnomalyScanRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[AnomalyDetectionResponse]]:
    service = AnomalyDetectionService(db)
    detections = await service.scan_recent_transactions(
        workspace_id=context.workspace_id,
        lookback_days=request.lookback_days,
        force_recheck=request.force_recheck,
    )
    dtos = [AnomalyDetectionService.map_to_dto(d) for d in detections]
    return ApiResponse(
        data=dtos,
        message=f"Scan complete. {len(dtos)} anomalous transactions identified.",
    )


@router.get(
    "/{anomaly_id}",
    response_model=ApiResponse[AnomalyDetectionResponse],
    summary="Get Anomaly Details",
    description="Retrieves full anomaly details, including transaction metadata, evidence parameters, and review history.",
)
async def get_anomaly_details(
    anomaly_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalyDetectionResponse]:
    repo = AnomalyRepository(db)
    anomaly = await repo.get_detection(anomaly_id, context.workspace_id)
    if not anomaly:
        raise NotFoundException(f"Anomaly {anomaly_id} not found in workspace.")

    return ApiResponse(
        data=AnomalyDetectionService.map_to_dto(anomaly),
        message="Anomaly details retrieved successfully.",
    )


# -------------------------------------------------------------------------
# Human Review Workflow
# -------------------------------------------------------------------------

@router.post(
    "/{anomaly_id}/review",
    response_model=ApiResponse[AnomalyDetectionResponse],
    summary="Submit Human Review Decision",
    description="Submits a review decision (acknowledge, mark expected, mark suspicious, dismiss, escalate) with optional whitelist exception.",
)
async def submit_anomaly_review(
    anomaly_id: uuid.UUID,
    request: AnomalyReviewRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalyDetectionResponse]:
    service = AnomalyReviewService(db)
    result = await service.review_anomaly(
        anomaly_id=anomaly_id,
        workspace_id=context.workspace_id,
        reviewer_id=context.user.id,
        request=request,
    )
    return ApiResponse(
        data=result,
        message=f"Review action '{request.action}' recorded successfully.",
    )


@router.post(
    "/{anomaly_id}/acknowledge",
    response_model=ApiResponse[AnomalyDetectionResponse],
    summary="Acknowledge Anomaly",
    description="Quick action to acknowledge an anomaly without dismissing or whitelisting.",
)
async def acknowledge_anomaly(
    anomaly_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalyDetectionResponse]:
    service = AnomalyReviewService(db)
    req = AnomalyReviewRequest(action="acknowledge", reason="Acknowledged by user")
    result = await service.review_anomaly(
        anomaly_id=anomaly_id,
        workspace_id=context.workspace_id,
        reviewer_id=context.user.id,
        request=req,
    )
    return ApiResponse(
        data=result,
        message="Anomaly acknowledged.",
    )


@router.post(
    "/{anomaly_id}/dismiss",
    response_model=ApiResponse[AnomalyDetectionResponse],
    summary="Dismiss Anomaly",
    description="Dismisses an anomaly alert as non-actionable or expected behavior.",
)
async def dismiss_anomaly(
    anomaly_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AnomalyDetectionResponse]:
    service = AnomalyReviewService(db)
    req = AnomalyReviewRequest(action="dismiss", reason=reason or "Dismissed by user")
    result = await service.review_anomaly(
        anomaly_id=anomaly_id,
        workspace_id=context.workspace_id,
        reviewer_id=context.user.id,
        request=req,
    )
    return ApiResponse(
        data=result,
        message="Anomaly dismissed.",
    )


# -------------------------------------------------------------------------
# Detection Rules & Exceptions
# -------------------------------------------------------------------------

@router.get(
    "/rules/list",
    response_model=ApiResponse[List[DetectionRuleResponse]],
    summary="List Detection Rules",
    description="Lists all detection rules active for this workspace, including global defaults and custom overrides.",
)
async def list_detection_rules(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[DetectionRuleResponse]]:
    repo = AnomalyRepository(db)
    rules = await repo.get_rules(context.workspace_id)
    dtos = [DetectionRuleResponse.model_validate(r) for r in rules]
    return ApiResponse(
        data=dtos,
        message=f"Retrieved {len(dtos)} detection rules.",
    )


@router.patch(
    "/rules/{rule_id}",
    response_model=ApiResponse[DetectionRuleResponse],
    summary="Update Detection Rule",
    description="Enables, disables, or adjusts threshold configurations for a detection rule.",
)
async def update_detection_rule(
    rule_id: uuid.UUID,
    request: DetectionRuleUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[DetectionRuleResponse]:
    service = AnomalyReviewService(db)
    updated = await service.update_rule(
        rule_id=rule_id,
        workspace_id=context.workspace_id,
        request=request,
    )
    return ApiResponse(
        data=DetectionRuleResponse.model_validate(updated),
        message=f"Detection rule '{updated.rule_code}' updated successfully.",
    )


@router.get(
    "/exceptions/list",
    response_model=ApiResponse[List[DetectionExceptionResponse]],
    summary="List Detection Whitelist Exceptions",
    description="Retrieves active whitelist exceptions suppressing alerts for merchants, categories, or accounts.",
)
async def list_detection_exceptions(
    include_expired: bool = Query(False),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[DetectionExceptionResponse]]:
    repo = AnomalyRepository(db)
    exceptions = await repo.list_exceptions(context.workspace_id, include_expired=include_expired)
    dtos = []
    for e in exceptions:
        dtos.append(
            DetectionExceptionResponse(
                id=e.id,
                workspace_id=e.workspace_id,
                rule_code=e.rule_code,
                merchant_id=e.merchant_id,
                merchant_name=e.merchant.name if getattr(e, "merchant", None) else None,
                category_id=e.category_id,
                category_name=e.category.name if getattr(e, "category", None) else None,
                account_id=e.account_id,
                account_name=e.account.name if getattr(e, "account", None) else None,
                merchant_name_pattern=e.merchant_name_pattern,
                max_amount_paise=e.max_amount_paise,
                max_amount=Decimal(e.max_amount_paise) / Decimal("100.0000") if e.max_amount_paise is not None else None,
                reason=e.reason,
                expires_at=e.expires_at,
                created_at=e.created_at,
            )
        )
    return ApiResponse(
        data=dtos,
        message=f"Retrieved {len(dtos)} detection exceptions.",
    )


@router.post(
    "/exceptions",
    response_model=ApiResponse[DetectionExceptionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Whitelist Exception",
    description="Creates a new detection whitelist exception for a merchant, category, or account.",
)
async def create_detection_exception(
    request: DetectionExceptionCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[DetectionExceptionResponse]:
    service = AnomalyReviewService(db)
    exc = await service.create_exception(
        workspace_id=context.workspace_id,
        user_id=context.user.id,
        request=request,
    )
    return ApiResponse(
        data=DetectionExceptionResponse(
            id=exc.id,
            workspace_id=exc.workspace_id,
            rule_code=exc.rule_code,
            merchant_id=exc.merchant_id,
            merchant_name=None,
            category_id=exc.category_id,
            category_name=None,
            account_id=exc.account_id,
            account_name=None,
            merchant_name_pattern=exc.merchant_name_pattern,
            max_amount_paise=exc.max_amount_paise,
            max_amount=Decimal(exc.max_amount_paise) / Decimal("100.0000") if exc.max_amount_paise is not None else None,
            reason=exc.reason,
            expires_at=exc.expires_at,
            created_at=exc.created_at,
        ),
        message="Detection exception created successfully.",
    )


@router.delete(
    "/exceptions/{exception_id}",
    response_model=ApiResponse[bool],
    summary="Delete Whitelist Exception",
    description="Removes a detection whitelist exception.",
)
async def delete_detection_exception(
    exception_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_ANOMALIES)),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[bool]:
    repo = AnomalyRepository(db)
    success = await repo.delete_exception(exception_id, context.workspace_id)
    if not success:
        raise NotFoundException(f"Detection exception {exception_id} not found.")

    await db.commit()
    return ApiResponse(
        data=True,
        message="Detection exception deleted successfully.",
    )
