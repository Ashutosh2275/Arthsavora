"""
Arthsavora V1 Double-Entry General Ledger Endpoints
Provides Chart of Accounts management, Accounting Periods,
Journal Entries, Balanced Posting, Compensating Reversals, and Trial Balance reporting.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_workspace_context, require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.infrastructure.database.session import get_db_session
from app.schemas.accounting import (
    AccountBalanceResponse,
    AccountingPeriodCreate,
    AccountingPeriodResponse,
    JournalEntryCreate,
    JournalEntryPostRequest,
    JournalEntryResponse,
    JournalEntryReverseRequest,
    JournalEntryUpdate,
    JournalListResponse,
    LedgerAccountCreate,
    LedgerAccountResponse,
    LedgerAccountUpdate,
    TrialBalanceResponse,
)
from app.services.ledger_service import LedgerService

router = APIRouter(tags=["General Ledger"])


def _format_journal_response(entry) -> JournalEntryResponse:
    """Helper to convert JournalEntry ORM model into JournalEntryResponse with line calculations."""
    lines_res = []
    total_debits = Decimal("0.0000")
    total_credits = Decimal("0.0000")

    for line in entry.lines:
        line_dict = {
            "id": line.id,
            "journal_entry_id": line.journal_entry_id,
            "ledger_account_id": line.ledger_account_id,
            "line_number": line.line_number,
            "entry_type": line.entry_type,
            "amount": line.amount,
            "amount_paise": line.amount_paise,
            "currency": line.currency,
            "description": line.description,
            "financial_account_id": line.financial_account_id,
            "counterparty_name": line.counterparty_name,
            "ledger_account_code": line.ledger_account.code if line.ledger_account else None,
            "ledger_account_name": line.ledger_account.name if line.ledger_account else None,
        }
        lines_res.append(line_dict)

        if line.entry_type == "debit":
            total_debits += line.amount
        elif line.entry_type == "credit":
            total_credits += line.amount

    return JournalEntryResponse(
        id=entry.id,
        workspace_id=entry.workspace_id,
        entry_number=entry.entry_number,
        entry_date=entry.entry_date,
        posting_date=entry.posting_date,
        status=entry.status,
        description=entry.description,
        source_type=entry.source_type,
        source_id=entry.source_id,
        reversal_of_entry_id=entry.reversal_of_entry_id,
        reversal_reason=entry.reversal_reason,
        accounting_period_id=entry.accounting_period_id,
        created_by=entry.created_by,
        posted_by_id=entry.posted_by_id,
        metadata_payload=entry.metadata_payload or {},
        lines=lines_res,
        total_debits=total_debits.quantize(Decimal("0.0001")),
        total_credits=total_credits.quantize(Decimal("0.0001")),
        is_balanced=(total_debits.quantize(Decimal("0.0001")) == total_credits.quantize(Decimal("0.0001"))),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


# ---------------------------------------------------------------------------
# Chart of Accounts Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/accounts",
    response_model=List[LedgerAccountResponse],
    summary="List Chart of Accounts ledger accounts",
)
async def list_ledger_accounts(
    is_active: Optional[bool] = Query(None, description="Filter active/inactive accounts"),
    account_type: Optional[str] = Query(None, description="asset, liability, equity, revenue, expense"),
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> List[LedgerAccountResponse]:
    service = LedgerService(session)
    accounts = await service.list_ledger_accounts(
        workspace_id=ctx.workspace.id,
        is_active=is_active,
        account_type=account_type,
    )
    return [LedgerAccountResponse.model_validate(a) for a in accounts]


@router.post(
    "/accounts",
    response_model=LedgerAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create custom ledger account",
)
async def create_ledger_account(
    payload: LedgerAccountCreate,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> LedgerAccountResponse:
    service = LedgerService(session)
    account = await service.create_ledger_account(
        workspace_id=ctx.workspace.id,
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type,
        normal_balance=payload.normal_balance,
        sub_type=payload.sub_type,
        description=payload.description,
        parent_id=payload.parent_id,
        linked_account_id=payload.linked_account_id,
    )
    await session.commit()
    return LedgerAccountResponse.model_validate(account)


@router.get(
    "/accounts/{ledger_account_id}",
    response_model=LedgerAccountResponse,
    summary="Get single ledger account details",
)
async def get_ledger_account(
    ledger_account_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> LedgerAccountResponse:
    service = LedgerService(session)
    account = await service.get_ledger_account(ctx.workspace.id, ledger_account_id)
    return LedgerAccountResponse.model_validate(account)


@router.patch(
    "/accounts/{ledger_account_id}",
    response_model=LedgerAccountResponse,
    summary="Update ledger account details",
)
async def update_ledger_account(
    ledger_account_id: uuid.UUID,
    payload: LedgerAccountUpdate,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> LedgerAccountResponse:
    service = LedgerService(session)
    account = await service.update_ledger_account(
        workspace_id=ctx.workspace.id,
        ledger_account_id=ledger_account_id,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    await session.commit()
    return LedgerAccountResponse.model_validate(account)


# ---------------------------------------------------------------------------
# Accounting Period Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/periods",
    response_model=List[AccountingPeriodResponse],
    summary="List accounting periods for workspace",
)
async def list_periods(
    fiscal_year: Optional[str] = Query(None, description="e.g. '2026-2027'"),
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> List[AccountingPeriodResponse]:
    service = LedgerService(session)
    periods = await service.list_periods(ctx.workspace.id, fiscal_year)
    return [AccountingPeriodResponse.model_validate(p) for p in periods]


@router.post(
    "/periods",
    response_model=AccountingPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new accounting period",
)
async def create_period(
    payload: AccountingPeriodCreate,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_PERIODS)),
    session: AsyncSession = Depends(get_db_session),
) -> AccountingPeriodResponse:
    service = LedgerService(session)
    period = await service.create_period(
        workspace_id=ctx.workspace.id,
        fiscal_year=payload.fiscal_year,
        period_number=payload.period_number,
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    await session.commit()
    return AccountingPeriodResponse.model_validate(period)


@router.post(
    "/periods/{period_id}/close",
    response_model=AccountingPeriodResponse,
    summary="Close an accounting period to prevent further postings",
)
async def close_period(
    period_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_PERIODS)),
    session: AsyncSession = Depends(get_db_session),
) -> AccountingPeriodResponse:
    service = LedgerService(session)
    period = await service.close_period(ctx.workspace.id, period_id, ctx.current_user.id)
    await session.commit()
    return AccountingPeriodResponse.model_validate(period)


@router.post(
    "/periods/{period_id}/reopen",
    response_model=AccountingPeriodResponse,
    summary="Reopen a closed accounting period",
)
async def reopen_period(
    period_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_PERIODS)),
    session: AsyncSession = Depends(get_db_session),
) -> AccountingPeriodResponse:
    service = LedgerService(session)
    period = await service.reopen_period(ctx.workspace.id, period_id, ctx.current_user.id)
    await session.commit()
    return AccountingPeriodResponse.model_validate(period)


# ---------------------------------------------------------------------------
# Journal Entry Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/journals",
    response_model=JournalListResponse,
    summary="List journal entries with pagination and filters",
)
async def list_journals(
    status: Optional[str] = Query(None, description="draft, posted, reversed"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> JournalListResponse:
    service = LedgerService(session)
    journals, total = await service.list_journals(
        workspace_id=ctx.workspace.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )
    items = [_format_journal_response(j) for j in journals]
    return JournalListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/journals",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create draft double-entry journal entry",
)
async def create_journal(
    payload: JournalEntryCreate,
    ctx: WorkspaceContext = Depends(require_permission(Permission.MANAGE_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    service = LedgerService(session)

    # Auto-generate entry number if omitted
    entry_number = payload.entry_number or f"JE-{payload.entry_date.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

    lines_data = [l.model_dump() for l in payload.lines]

    entry = await service.create_draft_journal(
        workspace_id=ctx.workspace.id,
        entry_number=entry_number,
        entry_date=payload.entry_date,
        description=payload.description,
        lines_data=lines_data,
        source_type=payload.source_type,
        source_id=payload.source_id,
        created_by=ctx.current_user.id,
        metadata_payload=payload.metadata,
    )
    await session.commit()
    # Reload with relationships
    loaded = await service.get_journal(ctx.workspace.id, entry.id)
    return _format_journal_response(loaded)


@router.get(
    "/journals/{journal_id}",
    response_model=JournalEntryResponse,
    summary="Get journal entry details with balanced lines",
)
async def get_journal(
    journal_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    service = LedgerService(session)
    entry = await service.get_journal(ctx.workspace.id, journal_id)
    return _format_journal_response(entry)


@router.post(
    "/journals/{journal_id}/post",
    response_model=JournalEntryResponse,
    summary="Post draft journal entry to authoritative general ledger",
)
async def post_journal(
    journal_id: uuid.UUID,
    payload: JournalEntryPostRequest = JournalEntryPostRequest(),
    ctx: WorkspaceContext = Depends(require_permission(Permission.POST_JOURNAL)),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    service = LedgerService(session)
    posted = await service.post_journal_entry(
        workspace_id=ctx.workspace.id,
        journal_id=journal_id,
        actor_id=ctx.current_user.id,
        correlation_id=payload.correlation_id,
    )
    await session.commit()
    loaded = await service.get_journal(ctx.workspace.id, posted.id)
    return _format_journal_response(loaded)


@router.post(
    "/journals/{journal_id}/reverse",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compensating reversal of posted journal entry",
)
async def reverse_journal(
    journal_id: uuid.UUID,
    payload: JournalEntryReverseRequest,
    ctx: WorkspaceContext = Depends(require_permission(Permission.REVERSE_JOURNAL)),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    service = LedgerService(session)
    reversal_number = payload.reversal_number or f"REV-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    reversal = await service.reverse_journal_entry(
        workspace_id=ctx.workspace.id,
        journal_id=journal_id,
        reversal_number=reversal_number,
        reason=payload.reason,
        actor_id=ctx.current_user.id,
    )
    await session.commit()
    loaded = await service.get_journal(ctx.workspace.id, reversal.id)
    return _format_journal_response(loaded)


# ---------------------------------------------------------------------------
# Account Balance & Trial Balance Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/accounts/{ledger_account_id}/balance",
    response_model=AccountBalanceResponse,
    summary="Get derived ledger account balance",
)
async def get_account_balance(
    ledger_account_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None, description="Point in time balance date"),
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> AccountBalanceResponse:
    service = LedgerService(session)
    balance_dict = await service.get_account_balance(ctx.workspace.id, ledger_account_id, as_of_date)
    return AccountBalanceResponse.model_validate(balance_dict)


@router.get(
    "/trial-balance",
    response_model=TrialBalanceResponse,
    summary="Get Trial Balance verifying Total Debits == Total Credits",
)
async def get_trial_balance(
    as_of_date: Optional[date] = Query(None, description="Point in time balance date"),
    ctx: WorkspaceContext = Depends(require_permission(Permission.VIEW_LEDGER)),
    session: AsyncSession = Depends(get_db_session),
) -> TrialBalanceResponse:
    service = LedgerService(session)
    tb_dict = await service.get_trial_balance(ctx.workspace.id, as_of_date)
    return TrialBalanceResponse.model_validate(tb_dict)
