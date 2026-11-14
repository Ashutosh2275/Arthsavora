"""
Arthsavora Financial Analytics API Endpoints
Authenticated, workspace-scoped RESTful routes for financial overviews, cash flow trends,
category/merchant spending breakdowns, balance sheets/net worth, period comparisons,
and sanitized CSV exports.
"""

from datetime import date
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import require_permission
from app.core.permissions import Permission, WorkspaceContext
from app.domain.analytics import (
    PeriodGrouping,
    ReportType,
    get_month_bounds,
)
from app.infrastructure.database.session import get_db_session
from app.schemas.analytics_schema import (
    CashFlowTrendsResponse,
    CategorySpendingResponse,
    FinancialOverviewResponse,
    MerchantSpendingResponse,
    NetWorthResponse,
    PeriodComparisonResponse,
)
from app.schemas.common import ApiResponse
from app.services.analytics.analytics_service import AnalyticsService

router = APIRouter(tags=["Financial Analytics & Insights"])


@router.get(
    "/overview",
    response_model=ApiResponse[FinancialOverviewResponse],
    summary="Financial Overview & Summary KPIs",
)
async def get_financial_overview(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 1st of current month)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Computes income, expenses, refunds, net cash flow, savings rate, and data quality indicators.
    Server-side aggregation from verified PostgreSQL records.
    """
    today = date.today()
    if not start_date or not end_date:
        m_start, _ = get_month_bounds(today)
        start_date = start_date or m_start
        end_date = end_date or today

    service = AnalyticsService(session)
    data = await service.get_overview(
        workspace_id=context.workspace_id,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        account_id=account_id,
    )
    return ApiResponse(data=FinancialOverviewResponse.model_validate(data))


@router.get(
    "/summary",
    response_model=ApiResponse[FinancialOverviewResponse],
    include_in_schema=False,
    summary="Financial Summary (Alias)",
)
async def get_financial_summary_alias(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    currency: str = Query("INR"),
    account_id: Optional[uuid.UUID] = Query(None),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """Backward-compatible alias for financial overview."""
    return await get_financial_overview(
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        account_id=account_id,
        context=context,
        session=session,
    )


@router.get(
    "/cash-flow",
    response_model=ApiResponse[CashFlowTrendsResponse],
    summary="Cash Flow Trends Over Time",
)
async def get_cash_flow_trends(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 90 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    grouping: PeriodGrouping = Query(PeriodGrouping.MONTH, description="Temporal interval (day, week, month, quarter, financial_year)"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves bucketed cash flow series (income, expense, net flow, cumulative flow)
    for interactive charting and trend inspection.
    """
    today = date.today()
    if not start_date or not end_date:
        start_date = start_date or (today.replace(day=1) if today.month > 2 else date(today.year - 1, 10, 1))
        end_date = end_date or today

    service = AnalyticsService(session)
    trends = await service.get_cash_flow_trends(
        workspace_id=context.workspace_id,
        start_date=start_date,
        end_date=end_date,
        grouping=grouping,
        currency=currency,
        account_id=account_id,
    )
    return ApiResponse(
        data=CashFlowTrendsResponse(
            currency=currency.upper(),
            grouping=grouping,
            start_date=start_date,
            end_date=end_date,
            trends=trends,
        )
    )


@router.get(
    "/categories",
    response_model=ApiResponse[CategorySpendingResponse],
    summary="Category Spending Distribution",
)
async def get_category_spending(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 1st of month)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    direction: str = Query("outflow", description="Direction filter ('outflow' or 'inflow')"),
    limit: int = Query(10, ge=1, le=50, description="Max categories to return"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns breakdown of expenditure by category with percentage distribution and transaction counts.
    Handles uncategorized transactions safely.
    """
    today = date.today()
    if not start_date or not end_date:
        m_start, _ = get_month_bounds(today)
        start_date = start_date or m_start
        end_date = end_date or today

    service = AnalyticsService(session)
    data = await service.get_category_spending(
        workspace_id=context.workspace_id,
        start_date=start_date,
        end_date=end_date,
        direction=direction,
        limit=limit,
        currency=currency,
        account_id=account_id,
    )
    return ApiResponse(data=CategorySpendingResponse.model_validate(data))


@router.get(
    "/merchants",
    response_model=ApiResponse[MerchantSpendingResponse],
    summary="Top Merchant Spending & Ticket Sizes",
)
async def get_merchant_spending(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 1st of month)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    limit: int = Query(10, ge=1, le=50, description="Max merchants to rank"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ranks top commercial merchants by total spend, transaction volume, and average ticket size.
    """
    today = date.today()
    if not start_date or not end_date:
        m_start, _ = get_month_bounds(today)
        start_date = start_date or m_start
        end_date = end_date or today

    service = AnalyticsService(session)
    data = await service.get_merchant_spending(
        workspace_id=context.workspace_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        currency=currency,
        account_id=account_id,
    )
    return ApiResponse(data=MerchantSpendingResponse.model_validate(data))


@router.get(
    "/net-worth",
    response_model=ApiResponse[NetWorthResponse],
    summary="Account Balances & Net Worth",
)
async def get_net_worth(
    currency: str = Query("INR", description="3-letter ISO currency code"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Derives real-time balance sheet position:
    Assets minus Liabilities equals Net Worth.
    """
    service = AnalyticsService(session)
    data = await service.get_net_worth(
        workspace_id=context.workspace_id,
        currency=currency,
    )
    return ApiResponse(data=NetWorthResponse.model_validate(data))


@router.get(
    "/comparison",
    response_model=ApiResponse[PeriodComparisonResponse],
    summary="Period-over-Period Performance Comparison",
)
async def get_period_comparison(
    current_start: date = Query(..., description="Current period start date"),
    current_end: date = Query(..., description="Current period end date"),
    previous_start: Optional[date] = Query(None, description="Prior period start (auto-computed if omitted)"),
    previous_end: Optional[date] = Query(None, description="Prior period end (auto-computed if omitted)"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Compares two periods with exact monetary deltas, percentage shifts, and directional favorability sentiments.
    """
    service = AnalyticsService(session)
    data = await service.get_comparison(
        workspace_id=context.workspace_id,
        current_start=current_start,
        current_end=current_end,
        previous_start=previous_start,
        previous_end=previous_end,
        currency=currency,
        account_id=account_id,
    )
    return ApiResponse(data=PeriodComparisonResponse.model_validate(data))


@router.get(
    "/export",
    summary="Export Financial Analytics as CSV",
    response_class=Response,
)
async def export_analytics_csv(
    report_type: ReportType = Query(ReportType.OVERVIEW, description="overview, cash_flow, categories, merchants, or net_worth"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    currency: str = Query("INR", description="3-letter ISO currency code"),
    account_id: Optional[uuid.UUID] = Query(None, description="Optional account filter"),
    context: WorkspaceContext = Depends(require_permission(Permission.EXPORT_ANALYTICS)),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Streams a sanitized CSV file of the requested analytics report.
    Protects against CSV formula injection.
    """
    today = date.today()
    if not start_date or not end_date:
        m_start, _ = get_month_bounds(today)
        start_date = start_date or m_start
        end_date = end_date or today

    service = AnalyticsService(session)
    csv_content = await service.export_analytics_csv(
        workspace_id=context.workspace_id,
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        account_id=account_id,
    )

    filename = f"arthsavora_{report_type.value}_{start_date}_{end_date}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
