"""
Arthsavora Multi-Tenant Row-Level Security (RLS) Infrastructure
Enforces defense-in-depth tenant isolation via PostgreSQL RLS and transaction-scoped context.
Guarantees zero connection pool context leakage using 'SET LOCAL'.
"""

import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Tenant-scoped tables subject to PostgreSQL Row-Level Security
RLS_TABLES = [
    # Core Financial & Identity
    "accounts",
    "transactions",
    "ledger_accounts",
    "journal_entries",
    "accounting_periods",
    "account_balance_snapshots",
    "categories",
    "merchants",
    "classification_rules",
    "transaction_classifications",
    "user_classification_feedback",
    "data_sources",
    "consent_records",
    "import_jobs",
    "import_batches",
    "import_candidates",
    "audit_logs",
    # Planning & Foresight
    "budgets",
    "budget_allocations",
    "budget_revisions",
    "budget_alerts",
    "financial_goals",
    "goal_activities",
    "recurring_definitions",
    "recurring_occurrences",
    "recurring_reminders",
    "recurring_suggestions",
    "subscriptions",
    "forecast_runs",
    "forecast_points",
    "forecast_evaluations",
    "financial_scenarios",
    # Anomaly & Risk Intelligence
    "anomaly_detections",
    "anomaly_reviews",
    "detection_rules",
    "detection_exceptions",
    # AI Assistant
    "assistant_conversations",
    "assistant_messages",
    "assistant_action_drafts",
    "assistant_usage_logs",
    # Document & Receipt Intelligence
    "financial_documents",
    "document_extractions",
    "document_reviews",
    "document_transaction_associations",
    # Unified Notifications
    "notifications",
    # Family Finance
    "family_profiles",
    "family_activities",
    "family_expense_allocations",
    "family_member_contributions",
    # Small Business Finance
    "business_profiles",
    "business_activities",
    "business_clients",
    "business_vendors",
    "business_invoices",
    "business_invoice_payments",
    "business_payables",
    "business_payable_payments",
    # Financial Data Connectivity & Account Aggregation
    "financial_connections",
    "financial_consents",
    "sync_jobs",
    "external_account_references",
    "connection_audit_events",
    "reconciliation_records",
    # Financial Reporting & Tax Intelligence
    "generated_reports",
    "report_validation_findings",
    "tax_classification_records",
    "tax_estimate_snapshots",
    # Membership & Invitations
    "workspace_members",
    "workspace_invitations",
]


async def set_tenant_context(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    """
    Sets the active workspace ID in the PostgreSQL transaction context.
    Uses 'SET LOCAL' so the variable is strictly scoped to the active transaction
    and is automatically discarded upon COMMIT or ROLLBACK.
    """
    stmt = text(f"SET LOCAL app.current_workspace_id = '{workspace_id}'")
    await session.execute(stmt)


async def reset_tenant_context(session: AsyncSession) -> None:
    """Explicitly resets the tenant workspace setting in the active connection."""
    stmt = text("SET LOCAL app.current_workspace_id = ''")
    await session.execute(stmt)


def generate_rls_sql() -> str:
    """
    Generates PostgreSQL DDL statements to enable RLS and create tenant isolation policies.
    Policies check that the record's workspace_id matches the session's 'app.current_workspace_id'.
    """
    statements = [
        "-- Arthsavora Row-Level Security (RLS) Policies",
    ]

    for table in RLS_TABLES:
        statements.extend([
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;",
            f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;",
            f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};",
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"FOR ALL USING (workspace_id = NULLIF(current_setting('app.current_workspace_id', true), '')::uuid);",
        ])

    return "\n".join(statements)
