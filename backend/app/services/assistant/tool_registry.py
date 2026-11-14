"""
Arthsavora AI Financial Tool Registry
Defines the authoritative catalog of financial service tools accessible to the assistant,
enforcing strict parameter schemas, required RBAC permissions, and sensitivity ratings.
"""

from typing import Any, Dict, List, Optional, Set
from app.core.permissions import Permission
from app.domain.assistant import DataSensitivityEnum, FinancialToolDefinitionVO


# Registry of all authorized assistant tools
FINANCIAL_TOOLS: Dict[str, FinancialToolDefinitionVO] = {
    # -------------------------------------------------------------------------
    # 1. Read-Only Analytics & Overview Tools
    # -------------------------------------------------------------------------
    "get_financial_overview": FinancialToolDefinitionVO(
        name="get_financial_overview",
        description="Retrieves high-level financial summary KPIs (inflow, outflow, net savings, transaction volume) for a specified date range.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "currency": {"type": "string", "default": "INR", "description": "ISO currency code"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_income_summary": FinancialToolDefinitionVO(
        name="get_income_summary",
        description="Retrieves total income earned and income source breakdown across categories for a specified period.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_expense_summary": FinancialToolDefinitionVO(
        name="get_expense_summary",
        description="Retrieves total expenses incurred, top spending categories, and proportion breakdown for a specified period.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_cash_flow": FinancialToolDefinitionVO(
        name="get_cash_flow",
        description="Retrieves bucketed cash flow trajectories (inflows, outflows, net savings) over time.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_category_spending": FinancialToolDefinitionVO(
        name="get_category_spending",
        description="Retrieves detailed spending breakdown by category, with optional filtering for a specific category (e.g., Food, Travel).",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "category_name": {"type": "string", "description": "Optional category name filter"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_merchant_spending": FinancialToolDefinitionVO(
        name="get_merchant_spending",
        description="Retrieves top merchants/counterparties sorted by cumulative expenditure volume.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                "limit": {"type": "integer", "default": 10, "description": "Max merchants to return"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["start_date", "end_date"],
        },
        required_permission=Permission.VIEW_ANALYTICS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),

    # -------------------------------------------------------------------------
    # 2. Account, Transaction & Ledger Tools
    # -------------------------------------------------------------------------
    "get_account_balances": FinancialToolDefinitionVO(
        name="get_account_balances",
        description="Retrieves verified balances across active liquid, savings, and credit card accounts.",
        parameters_schema={"type": "object", "properties": {}},
        required_permission=Permission.VIEW_ACCOUNTS.value,
        sensitivity=DataSensitivityEnum.CONFIDENTIAL,
        timeout_seconds=10,
    ),
    "search_transactions": FinancialToolDefinitionVO(
        name="search_transactions",
        description="Searches recent financial transactions by date range, minimum amount, or keyword.",
        parameters_schema={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Optional ISO start date"},
                "end_date": {"type": "string", "description": "Optional ISO end date"},
                "min_amount_paise": {"type": "integer", "description": "Optional minimum amount in paise"},
                "category_name": {"type": "string", "description": "Optional category filter"},
                "query": {"type": "string", "description": "Optional search term for description"},
                "limit": {"type": "integer", "default": 10, "description": "Max results (capped at 25)"},
            },
        },
        required_permission=Permission.VIEW_TRANSACTIONS.value,
        sensitivity=DataSensitivityEnum.CONFIDENTIAL,
        timeout_seconds=15,
    ),

    # -------------------------------------------------------------------------
    # 3. Budgets, Goals & Commitments Tools
    # -------------------------------------------------------------------------
    "get_budget_status": FinancialToolDefinitionVO(
        name="get_budget_status",
        description="Retrieves current active budgets, spending limits, actual expenditure, remaining capacity, and utilization percentage.",
        parameters_schema={
            "type": "object",
            "properties": {
                "category_name": {"type": "string", "description": "Optional category name filter"},
            },
        },
        required_permission=Permission.VIEW_BUDGETS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "get_goal_progress": FinancialToolDefinitionVO(
        name="get_goal_progress",
        description="Retrieves financial savings goals, target amounts, current accumulated savings, and percentage progress.",
        parameters_schema={"type": "object", "properties": {}},
        required_permission=Permission.VIEW_GOALS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "get_upcoming_commitments": FinancialToolDefinitionVO(
        name="get_upcoming_commitments",
        description="Retrieves scheduled upcoming bills, rent, utility payments, and EMIs due in the specified window.",
        parameters_schema={
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "default": 14, "description": "Number of days forward to check (default 14)"},
            },
        },
        required_permission=Permission.VIEW_RECURRING.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "get_subscription_summary": FinancialToolDefinitionVO(
        name="get_subscription_summary",
        description="Retrieves all active recurring subscriptions, recurring billing frequencies, and total monthly recurring burn.",
        parameters_schema={"type": "object", "properties": {}},
        required_permission=Permission.VIEW_SUBSCRIPTIONS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),

    # -------------------------------------------------------------------------
    # 4. Forecasting & Anomaly Tools
    # -------------------------------------------------------------------------
    "get_forecast": FinancialToolDefinitionVO(
        name="get_forecast",
        description="Retrieves projected 30-day cash flow, predicted income, projected expense trajectories, and confidence bounds.",
        parameters_schema={
            "type": "object",
            "properties": {
                "horizon_days": {"type": "integer", "default": 30, "description": "Forecast horizon (default 30 days)"},
            },
        },
        required_permission=Permission.VIEW_FORECASTS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=15,
    ),
    "get_anomaly_details": FinancialToolDefinitionVO(
        name="get_anomaly_details",
        description="Retrieves recent financial anomalies, spending spikes, or unusual transaction alerts.",
        parameters_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 5, "description": "Max anomalies to return"},
            },
        },
        required_permission=Permission.VIEW_ANOMALIES.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),

    # -------------------------------------------------------------------------
    # 5. Safe Action Proposal Tools (Draft Creation Only)
    # -------------------------------------------------------------------------
    "create_budget_draft": FinancialToolDefinitionVO(
        name="create_budget_draft",
        description="Proposes a new monthly budget draft for user confirmation. Does NOT mutate active budgets until confirmed.",
        parameters_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Budget name"},
                "limit_paise": {"type": "integer", "description": "Spending limit in paise"},
                "category_name": {"type": "string", "description": "Optional category name"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["name", "limit_paise"],
        },
        required_permission=Permission.MANAGE_BUDGETS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "create_goal_draft": FinancialToolDefinitionVO(
        name="create_goal_draft",
        description="Proposes a new financial savings goal draft for user confirmation. Does NOT create goal until confirmed.",
        parameters_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Goal name"},
                "target_amount_paise": {"type": "integer", "description": "Target amount in paise"},
                "target_date": {"type": "string", "description": "ISO target completion date"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["name", "target_amount_paise"],
        },
        required_permission=Permission.MANAGE_GOALS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "create_recurring_draft": FinancialToolDefinitionVO(
        name="create_recurring_draft",
        description="Proposes a new recurring subscription or payment schedule for user confirmation.",
        parameters_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Subscription or payee name"},
                "expected_amount_paise": {"type": "integer", "description": "Expected payment in paise"},
                "frequency": {"type": "string", "default": "monthly"},
                "currency": {"type": "string", "default": "INR"},
            },
            "required": ["name", "expected_amount_paise"],
        },
        required_permission=Permission.MANAGE_RECURRING.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "prepare_transaction_filter": FinancialToolDefinitionVO(
        name="prepare_transaction_filter",
        description="Generates a pre-configured search filter URL and filter configuration for the transaction ledger.",
        parameters_schema={
            "type": "object",
            "properties": {
                "filter_name": {"type": "string", "description": "Descriptive title for the filter"},
                "criteria": {"type": "object", "description": "Filter criteria key-value pairs"},
            },
            "required": ["filter_name", "criteria"],
        },
        required_permission=Permission.VIEW_TRANSACTIONS.value,
        sensitivity=DataSensitivityEnum.INTERNAL,
        timeout_seconds=5,
    ),
    "search_documents": FinancialToolDefinitionVO(
        name="search_documents",
        description="Searches and lists recent uploaded financial receipts, invoices, and supporting documents in the workspace.",
        parameters_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status: pending, extracted, review_required, confirmed, rejected"},
                "document_type": {"type": "string", "description": "Filter by type: receipt, invoice, bill"},
                "search": {"type": "string", "description": "Search query matching filename or merchant"},
                "limit": {"type": "integer", "default": 10},
            },
        },
        required_permission=Permission.VIEW_DOCUMENTS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "get_document_details": FinancialToolDefinitionVO(
        name="get_document_details",
        description="Retrieves complete structured extraction details, merchant, date, total amount, taxes, line items, and linked transaction for a specific document.",
        parameters_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "UUID of the financial document"},
            },
            "required": ["document_id"],
        },
        required_permission=Permission.VIEW_DOCUMENTS.value,
        sensitivity=DataSensitivityEnum.RESTRICTED_FINANCIAL,
        timeout_seconds=10,
    ),
    "get_unread_notifications": FinancialToolDefinitionVO(
        name="get_unread_notifications",
        description="Retrieves the user's unread notifications and alerts (budget warnings, upcoming bills, anomalies).",
        parameters_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 5},
            },
        },
        required_permission=Permission.VIEW_NOTIFICATIONS.value,
        sensitivity=DataSensitivityEnum.CONFIDENTIAL,
        timeout_seconds=10,
    ),
}


def get_tool_definition(tool_name: str) -> Optional[FinancialToolDefinitionVO]:
    """Retrieves definition contract for a registered tool."""
    return FINANCIAL_TOOLS.get(tool_name)


def list_available_tools_for_user(user_permissions: Set[str]) -> List[FinancialToolDefinitionVO]:
    """Filters registered tools by the active user's verified permissions."""
    return [
        tool for tool in FINANCIAL_TOOLS.values()
        if tool.required_permission in user_permissions
    ]
