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
    "accounts",
    "transactions",
    "ledger_accounts",
    "journal_entries",
    "data_sources",
    "consent_records",
    "import_jobs",
    "audit_logs",
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
