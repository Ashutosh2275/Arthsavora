"""
Initialize and apply accounting triggers to test database arthsavora_test.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.infrastructure.database.base import Base
import app.infrastructure.database.models

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/arthsavora_test"

async def setup():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
        print("Base metadata created in arthsavora_test.")

        # Trigger 1: balanced posting
        await conn.execute(text("""
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
        """))

        await conn.execute(text("DROP TRIGGER IF EXISTS trg_journal_balanced_deferred ON journal_entries"))
        await conn.execute(text("""
        CREATE CONSTRAINT TRIGGER trg_journal_balanced_deferred
        AFTER INSERT OR UPDATE OF status ON journal_entries
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION check_journal_entry_balanced_deferred()
        """))

        # Trigger 2: prevent line mutation or deletion for posted journals
        await conn.execute(text("""
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
        """))

        await conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_posted_line_mutation ON journal_lines"))
        await conn.execute(text("""
        CREATE TRIGGER trg_prevent_posted_line_mutation
        BEFORE UPDATE OR DELETE ON journal_lines
        FOR EACH ROW
        EXECUTE FUNCTION prevent_posted_journal_mutation()
        """))

        # Trigger 3: prevent deletion of posted journal entries
        await conn.execute(text("""
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
        """))

        await conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_posted_journal_deletion ON journal_entries"))
        await conn.execute(text("""
        CREATE TRIGGER trg_prevent_posted_journal_deletion
        BEFORE DELETE ON journal_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_posted_journal_deletion()
        """))

        print("All accounting triggers successfully installed in arthsavora_test.")

if __name__ == "__main__":
    asyncio.run(setup())
