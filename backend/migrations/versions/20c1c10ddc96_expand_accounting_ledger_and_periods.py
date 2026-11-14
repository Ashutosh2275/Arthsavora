"""expand_accounting_ledger_and_periods

Revision ID: 20c1c10ddc96
Revises: 52bcac9ccfef
Create Date: 2026-11-14 06:24:14.981199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20c1c10ddc96'
down_revision: Union[str, None] = '52bcac9ccfef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create accounting_periods table
    op.create_table(
        'accounting_periods',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('fiscal_year', sa.String(length=20), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("status IN ('open', 'closed')", name='chk_period_status'),
        sa.CheckConstraint('start_date <= end_date', name='chk_period_dates'),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'fiscal_year', 'period_number', name='uq_workspace_fy_period')
    )
    op.create_index('ix_accounting_periods_workspace_dates', 'accounting_periods', ['workspace_id', 'start_date', 'end_date'], unique=False)
    op.create_index(op.f('ix_accounting_periods_workspace_id'), 'accounting_periods', ['workspace_id'], unique=False)

    # 2. Expand journal_entries table
    op.add_column('journal_entries', sa.Column('reversal_reason', sa.String(length=500), nullable=True))
    op.add_column('journal_entries', sa.Column('accounting_period_id', sa.UUID(), nullable=True))
    op.add_column('journal_entries', sa.Column('posted_by_id', sa.UUID(), nullable=True))
    op.add_column('journal_entries', sa.Column('metadata_payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.create_foreign_key('fk_journal_entries_posted_by', 'journal_entries', 'users', ['posted_by_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_journal_entries_period', 'journal_entries', 'accounting_periods', ['accounting_period_id'], ['id'], ondelete='RESTRICT')

    # 3. Expand journal_lines table
    op.add_column('journal_lines', sa.Column('amount_paise', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('journal_lines', sa.Column('financial_account_id', sa.UUID(), nullable=True))
    op.add_column('journal_lines', sa.Column('counterparty_name', sa.String(length=255), nullable=True))
    op.add_column('journal_lines', sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.create_foreign_key('fk_journal_lines_financial_account', 'journal_lines', 'accounts', ['financial_account_id'], ['id'], ondelete='SET NULL')

    # Backfill amount_paise from amount
    op.execute("UPDATE journal_lines SET amount_paise = ROUND(amount * 100)::bigint WHERE amount_paise = 0 AND amount IS NOT NULL")

    # 4. Expand ledger_accounts table
    op.add_column('ledger_accounts', sa.Column('sub_type', sa.String(length=50), nullable=True))
    op.add_column('ledger_accounts', sa.Column('description', sa.String(length=500), nullable=True))
    op.add_column('ledger_accounts', sa.Column('parent_id', sa.UUID(), nullable=True))
    op.add_column('ledger_accounts', sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_foreign_key('fk_ledger_accounts_parent', 'ledger_accounts', 'ledger_accounts', ['parent_id'], ['id'], ondelete='SET NULL')

    # 5. Database-Level Invariant Triggers & Functions (Separate op.execute calls for asyncpg)
    # 5a. Function for balanced posting
    op.execute("""
    CREATE OR REPLACE FUNCTION check_journal_entry_balanced_deferred()
    RETURNS TRIGGER AS $$
    DECLARE
        v_debit_sum NUMERIC(18, 4);
        v_credit_sum NUMERIC(18, 4);
        v_line_count INTEGER;
    BEGIN
        IF NEW.status = 'posted' THEN
            SELECT 
                COALESCE(SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END), 0),
                COUNT(*)
            INTO v_debit_sum, v_credit_sum, v_line_count
            FROM journal_lines
            WHERE journal_entry_id = NEW.id;

            IF v_line_count < 2 THEN
                RAISE EXCEPTION 'Posted journal entry % must have at least 2 lines (found %)', NEW.id, v_line_count
                    USING ERRCODE = 'P0001';
            END IF;

            IF v_debit_sum <> v_credit_sum THEN
                RAISE EXCEPTION 'Unbalanced posted journal entry %: Debits (%) <> Credits (%)', NEW.id, v_debit_sum, v_credit_sum
                    USING ERRCODE = 'P0001';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_journal_balanced_deferred ON journal_entries;")
    op.execute("""
    CREATE CONSTRAINT TRIGGER trg_journal_balanced_deferred
    AFTER INSERT OR UPDATE OF status ON journal_entries
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION check_journal_entry_balanced_deferred();
    """)

    # 5b. Function & trigger for line immutability
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
    RETURNS TRIGGER AS $$
    DECLARE
        v_status VARCHAR(20);
        v_entry_id UUID;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            v_entry_id := OLD.journal_entry_id;
        ELSE
            v_entry_id := NEW.journal_entry_id;
        END IF;

        SELECT status INTO v_status FROM journal_entries WHERE id = v_entry_id;

        IF v_status = 'posted' THEN
            RAISE EXCEPTION 'Cannot modify or delete journal lines belonging to a posted journal entry.'
                USING ERRCODE = 'P0002';
        END IF;

        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        ELSE
            RETURN NEW;
        END IF;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_line_mutation ON journal_lines;")
    op.execute("""
    CREATE TRIGGER trg_prevent_posted_line_mutation
    BEFORE UPDATE OR DELETE ON journal_lines
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_mutation();
    """)

    # 5c. Function & trigger to prevent deletion of posted journals
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_posted_journal_deletion()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.status = 'posted' THEN
            RAISE EXCEPTION 'Cannot delete a posted journal entry. Must use formal reversal.'
                USING ERRCODE = 'P0003';
        END IF;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_journal_deletion ON journal_entries;")
    op.execute("""
    CREATE TRIGGER trg_prevent_posted_journal_deletion
    BEFORE DELETE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_deletion();
    """)


def downgrade() -> None:
    # 1. Drop Triggers and Functions
    op.execute("DROP TRIGGER IF EXISTS trg_journal_balanced_deferred ON journal_entries;")
    op.execute("DROP FUNCTION IF EXISTS check_journal_entry_balanced_deferred();")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_line_mutation ON journal_lines;")
    op.execute("DROP FUNCTION IF EXISTS prevent_posted_journal_mutation();")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_posted_journal_deletion ON journal_entries;")
    op.execute("DROP FUNCTION IF EXISTS prevent_posted_journal_deletion();")

    # 2. Revert Column and Table Changes
    op.drop_constraint('fk_ledger_accounts_parent', 'ledger_accounts', type_='foreignkey')
    op.drop_column('ledger_accounts', 'is_system')
    op.drop_column('ledger_accounts', 'parent_id')
    op.drop_column('ledger_accounts', 'description')
    op.drop_column('ledger_accounts', 'sub_type')

    op.drop_constraint('fk_journal_lines_financial_account', 'journal_lines', type_='foreignkey')
    op.drop_column('journal_lines', 'source_metadata')
    op.drop_column('journal_lines', 'counterparty_name')
    op.drop_column('journal_lines', 'financial_account_id')
    op.drop_column('journal_lines', 'amount_paise')

    op.drop_constraint('fk_journal_entries_period', 'journal_entries', type_='foreignkey')
    op.drop_constraint('fk_journal_entries_posted_by', 'journal_entries', type_='foreignkey')
    op.drop_column('journal_entries', 'metadata_payload')
    op.drop_column('journal_entries', 'posted_by_id')
    op.drop_column('journal_entries', 'accounting_period_id')
    op.drop_column('journal_entries', 'reversal_reason')

    op.drop_index(op.f('ix_accounting_periods_workspace_id'), table_name='accounting_periods')
    op.drop_index('ix_accounting_periods_workspace_dates', table_name='accounting_periods')
    op.drop_table('accounting_periods')
