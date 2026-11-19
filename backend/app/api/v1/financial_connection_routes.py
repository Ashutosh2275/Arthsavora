"""
Arthsavora Financial Connection & Account Aggregator API Endpoints
REST endpoints for provider discovery, consent initiation, authorization confirmation,
account discovery, linking, idempotent synchronization, and reconciliation.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db_session
from app.schemas.financial_connection_schema import (
    AuthorizeConnectionRequest,
    DiscoveredAccountResponse,
    FinancialConnectionResponse,
    FinancialProviderResponse,
    InitiateConnectionRequest,
    LinkAccountRequest,
    ReconciliationRecordResponse,
    ResolveReconciliationRequest,
    RevokeConsentRequest,
    SyncJobResponse,
    TriggerSyncRequest,
)
from app.services.financial_connection_service import FinancialConnectionService

router = APIRouter(tags=["Financial Connections & Account Aggregation"])


# ---------------------------------------------------------------------------
# Provider Catalog
# ---------------------------------------------------------------------------
@router.get(
    "/financial-providers",
    response_model=List[FinancialProviderResponse],
    summary="List available financial data providers and Account Aggregators",
)
async def list_financial_providers(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    service = FinancialConnectionService(session)
    providers = await service.list_providers()
    return providers


# ---------------------------------------------------------------------------
# Financial Connections Management
# ---------------------------------------------------------------------------
@router.get(
    "/financial-connections",
    response_model=List[FinancialConnectionResponse],
    summary="List all active financial connections for current workspace",
)
async def list_financial_connections(
    status: Optional[str] = Query(None, description="Filter by connection status"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    connections = await service.repo.list_connections(context.workspace_id, status=status)
    results = []
    for conn in connections:
        active_consent = await service.repo.get_active_consent_by_connection(conn.id)
        refs = await service.repo.list_account_references(conn.id)
        results.append(
            FinancialConnectionResponse(
                id=conn.id,
                workspace_id=conn.workspace_id,
                user_id=conn.user_id,
                provider_id=conn.provider_id,
                provider_code=conn.provider.provider_code if conn.provider else None,
                provider_name=conn.provider.name if conn.provider else None,
                institution_id=conn.institution_id,
                institution_name=conn.institution_name,
                status=conn.status,
                health_status=conn.health_status,
                authorization_url=conn.authorization_url,
                authorized_at=conn.authorized_at,
                expires_at=conn.expires_at,
                last_attempted_sync_at=conn.last_attempted_sync_at,
                last_successful_sync_at=conn.last_successful_sync_at,
                sync_failure_count=conn.sync_failure_count,
                last_error_code=conn.last_error_code,
                last_error_message=conn.last_error_message,
                sync_schedule=conn.sync_schedule,
                created_at=conn.created_at,
                active_consent=active_consent,
                account_references=refs,
            )
        )
    return results


@router.post(
    "/financial-connections",
    response_model=FinancialConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new financial connection and consent request",
)
async def initiate_financial_connection(
    payload: InitiateConnectionRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    connection, consent = await service.initiate_connection(
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        provider_code=payload.provider_code,
        institution_id=payload.institution_id,
        institution_name=payload.institution_name,
        purpose=payload.purpose,
        purpose_code=payload.purpose_code,
        data_categories=payload.data_categories,
        account_types=payload.account_types,
        valid_days=payload.valid_days,
        sync_schedule=payload.sync_schedule,
    )
    return FinancialConnectionResponse(
        id=connection.id,
        workspace_id=connection.workspace_id,
        user_id=connection.user_id,
        provider_id=connection.provider_id,
        provider_code=connection.provider.provider_code if connection.provider else None,
        provider_name=connection.provider.name if connection.provider else None,
        institution_id=connection.institution_id,
        institution_name=connection.institution_name,
        status=connection.status,
        health_status=connection.health_status,
        authorization_url=connection.authorization_url,
        authorized_at=connection.authorized_at,
        expires_at=connection.expires_at,
        last_attempted_sync_at=connection.last_attempted_sync_at,
        last_successful_sync_at=connection.last_successful_sync_at,
        sync_failure_count=connection.sync_failure_count,
        last_error_code=connection.last_error_code,
        last_error_message=connection.last_error_message,
        sync_schedule=connection.sync_schedule,
        created_at=connection.created_at,
        active_consent=consent,
        account_references=[],
    )


@router.get(
    "/financial-connections/{connection_id}",
    response_model=FinancialConnectionResponse,
    summary="Retrieve details for a specific financial connection",
)
async def get_financial_connection(
    connection_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    conn = await service.repo.get_connection(context.workspace_id, connection_id)
    if not conn:
        raise NotFoundException("Financial connection not found.")

    active_consent = await service.repo.get_active_consent_by_connection(conn.id)
    refs = await service.repo.list_account_references(conn.id)
    return FinancialConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        user_id=conn.user_id,
        provider_id=conn.provider_id,
        provider_code=conn.provider.provider_code if conn.provider else None,
        provider_name=conn.provider.name if conn.provider else None,
        institution_id=conn.institution_id,
        institution_name=conn.institution_name,
        status=conn.status,
        health_status=conn.health_status,
        authorization_url=conn.authorization_url,
        authorized_at=conn.authorized_at,
        expires_at=conn.expires_at,
        last_attempted_sync_at=conn.last_attempted_sync_at,
        last_successful_sync_at=conn.last_successful_sync_at,
        sync_failure_count=conn.sync_failure_count,
        last_error_code=conn.last_error_code,
        last_error_message=conn.last_error_message,
        sync_schedule=conn.sync_schedule,
        created_at=conn.created_at,
        active_consent=active_consent,
        account_references=refs,
    )


@router.post(
    "/financial-connections/{connection_id}/authorize",
    response_model=FinancialConnectionResponse,
    summary="Confirm authorization handoff and discover connected accounts",
)
async def authorize_financial_connection(
    connection_id: UUID,
    payload: Optional[AuthorizeConnectionRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    handle = payload.provider_consent_handle if payload else None
    conn = await service.authorize_connection(
        connection_id=connection_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        provider_consent_handle=handle,
    )
    active_consent = await service.repo.get_active_consent_by_connection(conn.id)
    refs = await service.repo.list_account_references(conn.id)
    return FinancialConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        user_id=conn.user_id,
        provider_id=conn.provider_id,
        provider_code=conn.provider.provider_code if conn.provider else None,
        provider_name=conn.provider.name if conn.provider else None,
        institution_id=conn.institution_id,
        institution_name=conn.institution_name,
        status=conn.status,
        health_status=conn.health_status,
        authorization_url=conn.authorization_url,
        authorized_at=conn.authorized_at,
        expires_at=conn.expires_at,
        last_attempted_sync_at=conn.last_attempted_sync_at,
        last_successful_sync_at=conn.last_successful_sync_at,
        sync_failure_count=conn.sync_failure_count,
        last_error_code=conn.last_error_code,
        last_error_message=conn.last_error_message,
        sync_schedule=conn.sync_schedule,
        created_at=conn.created_at,
        active_consent=active_consent,
        account_references=refs,
    )


@router.post(
    "/financial-connections/{connection_id}/sync",
    response_model=SyncJobResponse,
    summary="Trigger on-demand transaction and balance synchronization",
)
async def trigger_connection_sync(
    connection_id: UUID,
    payload: Optional[TriggerSyncRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.SYNC_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    job_type = payload.job_type if payload else "manual_sync"
    sync_job = await service.sync_connection(
        connection_id=connection_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        job_type=job_type,
    )
    return sync_job


@router.post(
    "/financial-connections/{connection_id}/revoke",
    response_model=FinancialConnectionResponse,
    summary="Revoke consent with financial provider",
)
async def revoke_financial_consent(
    connection_id: UUID,
    payload: Optional[RevokeConsentRequest] = None,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    reason = payload.reason if payload else "User requested revocation"
    conn = await service.revoke_consent(
        connection_id=connection_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        reason=reason,
    )
    active_consent = await service.repo.get_active_consent_by_connection(conn.id)
    refs = await service.repo.list_account_references(conn.id)
    return FinancialConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        user_id=conn.user_id,
        provider_id=conn.provider_id,
        provider_code=conn.provider.provider_code if conn.provider else None,
        provider_name=conn.provider.name if conn.provider else None,
        institution_id=conn.institution_id,
        institution_name=conn.institution_name,
        status=conn.status,
        health_status=conn.health_status,
        authorization_url=conn.authorization_url,
        authorized_at=conn.authorized_at,
        expires_at=conn.expires_at,
        last_attempted_sync_at=conn.last_attempted_sync_at,
        last_successful_sync_at=conn.last_successful_sync_at,
        sync_failure_count=conn.sync_failure_count,
        last_error_code=conn.last_error_code,
        last_error_message=conn.last_error_message,
        sync_schedule=conn.sync_schedule,
        created_at=conn.created_at,
        active_consent=active_consent,
        account_references=refs,
    )


@router.delete(
    "/financial-connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect external financial connection and unlink accounts",
)
async def disconnect_financial_connection(
    connection_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    await service.disconnect_connection(connection_id, context.workspace_id, context.user_id)
    return None


# ---------------------------------------------------------------------------
# Account Discovery & Linking
# ---------------------------------------------------------------------------
@router.get(
    "/financial-connections/{connection_id}/accounts",
    response_model=List[DiscoveredAccountResponse],
    summary="List discovered accounts for a connection",
)
async def list_connection_accounts(
    connection_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    conn = await service.repo.get_connection(context.workspace_id, connection_id)
    if not conn:
        raise NotFoundException("Financial connection not found.")
    refs = await service.repo.list_account_references(connection_id)
    return refs


@router.post(
    "/financial-connections/{connection_id}/accounts/{ref_id}/link",
    response_model=DiscoveredAccountResponse,
    summary="Link a discovered external account to an Arthsavora account",
)
async def link_external_account(
    connection_id: UUID,
    ref_id: UUID,
    payload: LinkAccountRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    ref = await service.link_account(
        connection_id=connection_id,
        external_ref_id=ref_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        existing_account_id=payload.existing_account_id,
        create_new=payload.create_new,
        account_name=payload.account_name,
    )
    return ref


@router.post(
    "/financial-connections/{connection_id}/accounts/{ref_id}/unlink",
    response_model=DiscoveredAccountResponse,
    summary="Unlink an external account",
)
async def unlink_external_account(
    connection_id: UUID,
    ref_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    ref = await service.unlink_account(
        connection_id=connection_id,
        external_ref_id=ref_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
    )
    return ref


# ---------------------------------------------------------------------------
# Sync History & Reconciliation
# ---------------------------------------------------------------------------
@router.get(
    "/financial-connections/{connection_id}/sync-history",
    response_model=List[SyncJobResponse],
    summary="List synchronization job history",
)
async def list_connection_sync_history(
    connection_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    conn = await service.repo.get_connection(context.workspace_id, connection_id)
    if not conn:
        raise NotFoundException("Financial connection not found.")
    jobs = await service.repo.list_sync_jobs(connection_id, limit=limit)
    return jobs


@router.get(
    "/financial-connections/{connection_id}/reconciliation",
    response_model=List[ReconciliationRecordResponse],
    summary="List reconciliation discrepancy records for a connection",
)
async def list_connection_reconciliation(
    connection_id: UUID,
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    records = await service.get_reconciliation_records(
        workspace_id=context.workspace_id,
        connection_id=connection_id,
    )
    return records


@router.post(
    "/financial-connections/{connection_id}/reconciliation/{rec_id}/resolve",
    response_model=ReconciliationRecordResponse,
    summary="Resolve reconciliation discrepancy with explanation",
)
async def resolve_reconciliation_record(
    connection_id: UUID,
    rec_id: UUID,
    payload: ResolveReconciliationRequest,
    context: WorkspaceContext = Depends(require_permission(Permission.MANAGE_FINANCIAL_CONNECTIONS)),
    session: AsyncSession = Depends(get_db_session),
):
    service = FinancialConnectionService(session)
    rec = await service.resolve_reconciliation(
        reconciliation_id=rec_id,
        workspace_id=context.workspace_id,
        user_id=context.user_id,
        explanation=payload.explanation,
    )
    return rec
