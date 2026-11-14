"""
Arthsavora Transaction Categorization, Merchant Intelligence & Rules Routes
Authenticated endpoints for categories, merchants, rules, classifications, and user feedback.
"""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_workspace_context, require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.domain.category_taxonomy import CategoryStatus
from app.infrastructure.database.session import get_db_session
from app.repositories.category_repository import CategoryRepository
from app.repositories.merchant_repository import MerchantRepository
from app.repositories.rule_repository import RuleRepository
from app.schemas.common import ApiResponse
from app.schemas.intelligence_schema import (
    BatchCategorizeRequest,
    BatchCategorizeResponse,
    CategoryCreateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
    ClassificationResponse,
    FeedbackResponse,
    FeedbackSubmitRequest,
    MerchantResponse,
    PreviewSuggestRequest,
    PreviewSuggestResponse,
    RuleCreateRequest,
    RuleResponse,
    RuleUpdateRequest,
)
from app.services.intelligence.categorization_service import CategorizationService
from app.services.intelligence.feedback_service import FeedbackService
from app.services.intelligence.ml_classifier import ml_classifier

router = APIRouter(tags=["Transaction Intelligence & Categories"])


# ===========================================================================
# 1. Category Management Endpoints
# ===========================================================================

@router.get(
    "/categories",
    response_model=ApiResponse[List[CategoryResponse]],
    summary="List Categories",
)
async def list_categories(
    category_type: Optional[str] = Query(None, description="income, expense, or transfer"),
    include_archived: bool = Query(False),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    # Ensure system categories are seeded if none exist
    system_cats = await repo.list_categories(workspace_id=None)
    if not system_cats:
        await repo.seed_system_categories()
        await session.commit()

    cats = await repo.list_categories(
        workspace_id=context.workspace.id,
        category_type=category_type,
        workspace_type=context.workspace.type,
        include_archived=include_archived,
    )
    return ApiResponse.success(data=[CategoryResponse.model_validate(c) for c in cats])


@router.get(
    "/categories/tree",
    response_model=ApiResponse[List[CategoryTreeResponse]],
    summary="Get Hierarchical Category Tree",
)
async def get_category_tree(
    category_type: Optional[str] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    system_cats = await repo.list_categories(workspace_id=None)
    if not system_cats:
        await repo.seed_system_categories()
        await session.commit()

    roots = await repo.get_tree(
        workspace_id=context.workspace.id,
        category_type=category_type,
        workspace_type=context.workspace.type,
    )
    return ApiResponse.success(data=[CategoryTreeResponse.model_validate(r) for r in roots])


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Category",
)
async def create_category(
    payload: CategoryCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    cat = await repo.create_category(
        name=payload.name,
        category_type=payload.category_type,
        workspace_id=context.workspace.id,
        parent_id=payload.parent_id,
        slug=payload.slug,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        workspace_type=payload.workspace_type,
        display_order=payload.display_order,
        is_system=False,
    )
    await session.commit()
    return ApiResponse.success(
        data=CategoryResponse.model_validate(cat),
        message="Category created successfully.",
    )


@router.get(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryResponse],
    summary="Get Category Details",
)
async def get_category(
    category_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    cat = await repo.get_by_id(category_id)
    if not cat:
        return ApiResponse.error(message="Category not found.", code="NOT_FOUND")
    return ApiResponse.success(data=CategoryResponse.model_validate(cat))


@router.patch(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryResponse],
    summary="Update Category",
)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    cat = await repo.update_category(
        category_id=category_id,
        name=payload.name,
        parent_id=payload.parent_id,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        status=payload.status,
        workspace_type=payload.workspace_type,
        display_order=payload.display_order,
    )
    await session.commit()
    return ApiResponse.success(
        data=CategoryResponse.model_validate(cat),
        message="Category updated successfully.",
    )


@router.delete(
    "/categories/{category_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Delete or Archive Category",
)
async def delete_category(
    category_id: uuid.UUID,
    reassign_to_id: Optional[uuid.UUID] = Query(None, description="Reassign transactions to this category"),
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CategoryRepository(session)
    await repo.delete_category(category_id, reassign_to_id=reassign_to_id)
    await session.commit()
    return ApiResponse.success(data={"deleted_id": str(category_id)}, message="Category deleted successfully.")


# ===========================================================================
# 2. Merchant Intelligence Endpoints
# ===========================================================================

@router.get(
    "/merchants",
    response_model=ApiResponse[List[MerchantResponse]],
    summary="List Recognized Merchants & Aliases",
)
async def list_merchants(
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = MerchantRepository(session)
    # Ensure system merchants are seeded
    merchants = await repo.list_merchants(workspace_id=context.workspace.id, search_query=search, limit=limit)
    if not merchants and not search:
        # Seed system categories first, then merchants
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories()
        await repo.seed_system_merchants()
        await session.commit()
        merchants = await repo.list_merchants(workspace_id=context.workspace.id, search_query=search, limit=limit)

    return ApiResponse.success(data=[MerchantResponse.model_validate(m) for m in merchants])


# ===========================================================================
# 3. Deterministic Classification Rule Endpoints
# ===========================================================================

@router.get(
    "/rules",
    response_model=ApiResponse[List[RuleResponse]],
    summary="List Classification Rules",
)
async def list_rules(
    include_disabled: bool = Query(False),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_RULES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepository(session)
    rules = await repo.list_rules(workspace_id=context.workspace.id, include_disabled=include_disabled)
    
    results = []
    for r in rules:
        resp = RuleResponse.model_validate(r)
        resp.suggested_category_name = r.suggested_category.name if r.suggested_category else None
        resp.suggested_merchant_name = r.suggested_merchant.canonical_name if r.suggested_merchant else None
        results.append(resp)

    return ApiResponse.success(data=results)


@router.post(
    "/rules",
    response_model=ApiResponse[RuleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Classification Rule",
)
async def create_rule(
    payload: RuleCreateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RULES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepository(session)
    rule = await repo.create_rule(
        workspace_id=context.workspace.id,
        name=payload.name,
        conditions=payload.conditions,
        suggested_category_id=payload.suggested_category_id,
        suggested_merchant_id=payload.suggested_merchant_id,
        priority=payload.priority,
        is_enabled=payload.is_enabled,
        rule_scope=payload.rule_scope,
        created_by_id=context.current_user.id,
    )
    await session.commit()
    return ApiResponse.success(
        data=RuleResponse.model_validate(rule),
        message="Classification rule created successfully.",
    )


@router.patch(
    "/rules/{rule_id}",
    response_model=ApiResponse[RuleResponse],
    summary="Update Classification Rule",
)
async def update_rule(
    rule_id: uuid.UUID,
    payload: RuleUpdateRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RULES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepository(session)
    rule = await repo.update_rule(
        workspace_id=context.workspace.id,
        rule_id=rule_id,
        name=payload.name,
        conditions=payload.conditions,
        suggested_category_id=payload.suggested_category_id,
        suggested_merchant_id=payload.suggested_merchant_id,
        priority=payload.priority,
        is_enabled=payload.is_enabled,
    )
    await session.commit()
    return ApiResponse.success(
        data=RuleResponse.model_validate(rule),
        message="Classification rule updated successfully.",
    )


@router.delete(
    "/rules/{rule_id}",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Delete Classification Rule",
)
async def delete_rule(
    rule_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_RULES)),
    session: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepository(session)
    await repo.delete_rule(workspace_id=context.workspace.id, rule_id=rule_id)
    await session.commit()
    return ApiResponse.success(data={"deleted_id": str(rule_id)}, message="Rule deleted successfully.")


# ===========================================================================
# 4. Transaction Categorization & Feedback Endpoints
# ===========================================================================

@router.post(
    "/transactions/{transaction_id}/categorize",
    response_model=ApiResponse[ClassificationResponse],
    summary="Categorize Transaction (Hybrid Decision Engine)",
)
async def categorize_transaction(
    transaction_id: uuid.UUID,
    force_reclassify: bool = Query(False),
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = CategorizationService(session)
    res = await service.categorize_transaction(
        workspace_id=context.workspace.id,
        transaction_id=transaction_id,
        actor_id=context.current_user.id,
        force_reclassify=force_reclassify,
    )
    await session.commit()
    return ApiResponse.success(data=ClassificationResponse(**res))


@router.post(
    "/transactions/batch-categorize",
    response_model=ApiResponse[BatchCategorizeResponse],
    summary="Batch Categorize Transactions",
)
async def batch_categorize_transactions(
    payload: BatchCategorizeRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = CategorizationService(session)
    results = []
    for tx_id in payload.transaction_ids:
        try:
            res = await service.categorize_transaction(
                workspace_id=context.workspace.id,
                transaction_id=tx_id,
                actor_id=context.current_user.id,
                force_reclassify=payload.force_reclassify,
            )
            results.append(ClassificationResponse(**res))
        except Exception:
            continue

    await session.commit()
    return ApiResponse.success(
        data=BatchCategorizeResponse(
            total_requested=len(payload.transaction_ids),
            categorized_count=len(results),
            results=results,
        )
    )


@router.get(
    "/transactions/{transaction_id}/classification",
    response_model=ApiResponse[Optional[ClassificationResponse]],
    summary="Get Transaction Classification & Explainability Details",
)
async def get_transaction_classification(
    transaction_id: uuid.UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_TRANSACTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = CategorizationService(session)
    cl = await service.intel_repo.get_classification_by_transaction_id(
        workspace_id=context.workspace.id,
        transaction_id=transaction_id,
    )
    if not cl:
        return ApiResponse.success(data=None, message="No classification record found.")

    res = {
        "classification_id": str(cl.id),
        "workspace_id": str(cl.workspace_id),
        "transaction_id": str(cl.transaction_id),
        "original_description": cl.transaction.description if cl.transaction else "",
        "normalized_description": cl.transaction.normalized_description if cl.transaction else None,
        "merchant_name": cl.suggested_merchant_name or (cl.transaction.merchant_name if cl.transaction else None),
        "suggested_category_id": str(cl.suggested_category_id),
        "suggested_category_name": cl.suggested_category.name if cl.suggested_category else "Uncategorized",
        "confidence_score": float(cl.confidence_score),
        "confidence_band": cl.confidence_band,
        "method": cl.method,
        "model_version": cl.model_version,
        "explanation": cl.explanation,
        "status": cl.status,
        "created_at": cl.created_at.isoformat() if cl.created_at else None,
    }
    return ApiResponse.success(data=ClassificationResponse(**res))


@router.post(
    "/transactions/{transaction_id}/feedback",
    response_model=ApiResponse[FeedbackResponse],
    summary="Submit User Feedback & Confirmation",
)
async def submit_transaction_feedback(
    transaction_id: uuid.UUID,
    payload: FeedbackSubmitRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_INTELLIGENCE)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FeedbackService(session)
    res = await service.submit_feedback(
        workspace_id=context.workspace.id,
        transaction_id=transaction_id,
        user_id=context.current_user.id,
        action=payload.action,
        confirmed_category_id=payload.confirmed_category_id,
        confirmed_merchant_name=payload.confirmed_merchant_name,
        feedback_reason=payload.feedback_reason,
        create_rule=payload.create_rule,
        rule_name=payload.rule_name,
    )
    await session.commit()
    return ApiResponse.success(data=FeedbackResponse(**res), message="Feedback recorded and applied.")


@router.post(
    "/categories/suggest",
    response_model=ApiResponse[PreviewSuggestResponse],
    summary="Live Text Categorization Preview",
)
async def preview_suggestion(
    payload: PreviewSuggestRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
    session: AsyncSession = Depends(get_db_session),
):
    service = CategorizationService(session)
    res = await service.preview_suggestion(
        description=payload.description,
        workspace_id=context.workspace.id,
        direction=payload.direction,
        amount_paise=payload.amount_paise,
    )
    return ApiResponse.success(data=PreviewSuggestResponse(**res))


@router.get(
    "/intelligence/model-info",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Get ML Model Metadata & Evaluation Metrics",
)
async def get_model_info(
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_CATEGORIES)),
):
    return ApiResponse.success(data=ml_classifier.metadata)
