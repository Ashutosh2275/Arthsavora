# ARTHSAVORA — General Ledger Integrity, Immutability & Constraint Architecture

## 1. Overview & Security Philosophy

The integrity of the Arthsavora General Ledger is non-negotiable. To achieve enterprise and commercial-grade fintech compliance in India, data integrity guarantees cannot rely exclusively on application-level logic; they must be physically enforced by the PostgreSQL relational engine itself.

---

## 2. Invariant Enforcement Hierarchy

```
+-------------------------------------------------------------------------+
| Level 1: Application Service & Domain Layer                             |
| - Pre-validates accounting period status (open vs closed)               |
| - Asserts sum(debit) == sum(credit) with exact Decimal/paise            |
| - Verifies minimum 2 lines and positive values                          |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| Level 2: Database Table Constraints                                     |
| - CHECK (amount > 0 AND amount_paise > 0)                               |
| - CHECK (entry_type IN ('debit', 'credit'))                             |
| - CHECK (status IN ('draft', 'posted', 'reversed'))                     |
| - Unique (workspace_id, fiscal_year, period_number)                     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| Level 3: PostgreSQL Database Triggers & Deferred Constraint Triggers    |
| - trg_journal_balanced_deferred: Asserts balanced debits & credits      |
| - trg_prevent_posted_line_mutation: Prevents UPDATE/DELETE on lines     |
| - trg_prevent_posted_journal_deletion: Prevents DELETE on journals      |
+-------------------------------------------------------------------------+
```

---

## 3. Database Triggers & Verification

### 3.1 Deferred Constraint Trigger: `trg_journal_balanced_deferred`
An ordinary table CHECK constraint cannot aggregate rows from child tables (`journal_lines`). PostgreSQL's `CONSTRAINT TRIGGER` with `DEFERRABLE INITIALLY DEFERRED` evaluates at transaction `COMMIT` time:

```sql
CREATE OR REPLACE FUNCTION check_journal_entry_balanced_deferred()
RETURNS TRIGGER AS $$
DECLARE
    v_status VARCHAR(20);
    v_total_debits NUMERIC(18, 4);
    v_total_credits NUMERIC(18, 4);
    v_line_count INTEGER;
BEGIN
    SELECT status INTO v_status FROM journal_entries WHERE id = NEW.id;
    
    -- Only evaluate when status is 'posted'
    IF v_status = 'posted' THEN
        SELECT 
            COALESCE(SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END), 0),
            COUNT(*)
        INTO v_total_debits, v_total_credits, v_line_count
        FROM journal_lines
        WHERE journal_entry_id = NEW.id;

        IF v_line_count < 2 THEN
            RAISE EXCEPTION 'Posted journal entry % must have at least 2 lines (found %)', 
                NEW.id, v_line_count USING ERRCODE = 'P0001';
        END IF;

        IF v_total_debits != v_total_credits THEN
            RAISE EXCEPTION 'Journal entry % is unbalanced: debits=% credits=%', 
                NEW.id, v_total_debits, v_total_credits USING ERRCODE = 'P0001';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_journal_balanced_deferred
AFTER INSERT OR UPDATE OF status ON journal_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION check_journal_entry_balanced_deferred();
```
*Guaranteed Result:* Even if a developer or administrator attempts an un-balanced `UPDATE journal_entries SET status = 'posted'`, PostgreSQL aborts the transaction with error `P0001`.

### 3.2 Immutability Trigger: `trg_prevent_posted_line_mutation`
Prevents modifying or deleting lines that belong to a posted or reversed entry:

```sql
CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
RETURNS TRIGGER AS $$
DECLARE
    v_status VARCHAR(20);
    v_target_id UUID;
BEGIN
    v_target_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.journal_entry_id ELSE NEW.journal_entry_id END;
    SELECT status INTO v_status FROM journal_entries WHERE id = v_target_id;
    
    IF v_status IN ('posted', 'reversed') THEN
        RAISE EXCEPTION 'Cannot % journal line belonging to % journal entry %', 
            TG_OP, v_status, v_target_id USING ERRCODE = 'P0002';
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_line_mutation
BEFORE UPDATE OR DELETE ON journal_lines
FOR EACH ROW
EXECUTE FUNCTION prevent_posted_journal_mutation();
```
*Guaranteed Result:* Attempting `UPDATE journal_lines SET amount = ...` or `DELETE FROM journal_lines WHERE ...` fails with SQLSTATE `P0002`.

### 3.3 Deletion Prevention Trigger: `trg_prevent_posted_journal_deletion`
Prevents direct deletion of posted or reversed journal entry records:

```sql
CREATE OR REPLACE FUNCTION prevent_posted_journal_deletion()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IN ('posted', 'reversed') THEN
        RAISE EXCEPTION 'Cannot delete % journal entry %', 
            OLD.status, OLD.id USING ERRCODE = 'P0003';
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_posted_journal_deletion
BEFORE DELETE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_posted_journal_deletion();
```
*Guaranteed Result:* Attempting `DELETE FROM journal_entries WHERE id = ...` fails with SQLSTATE `P0003`.

---

## 4. Reversal and Correction Protocols

1. **Strict Non-Destructive Policy:** Once posted, journal entries are permanent historical facts. They can never be altered or purged.
2. **Compensating Reversal Process:**
   - Every original line is copied into a new journal entry with opposite polarity (debits become credits, credits become debits).
   - The compensating entry links back via `reversal_of_entry_id`.
   - A non-empty human-authored `reversal_reason` is strictly required.
   - The original entry is marked `reversed`.
   - Both original and reversal entries remain visible in all audits and general ledger ledgers.
