# Arthsavora Financial Analytics Performance & Optimization

## 1. Overview & Latency Targets

Financial dashboards are the first screen loaded by users upon login. Unresponsive aggregations immediately degrade confidence in a FinTech application. Arthsavora targets the following performance budgets:

- **Financial Overview:** $< 50\text{ ms}$ query latency for workspaces with $\le 500,000$ transactions.
- **Cash Flow Trends:** $< 70\text{ ms}$ for multi-year monthly groupings.
- **Category & Merchant Ranking:** $< 60\text{ ms}$ including joins and dynamic percentage calculation.
- **CSV Streaming:** Direct streaming from buffer with zero disk write overhead.

---

## 2. Server-Side PostgreSQL Indexing Strategy

All analytics aggregation queries leverage existing composite indices defined on the `transactions` and `accounts` tables:

```sql
-- 1. Date Range & Workspace Isolation
CREATE INDEX ix_transactions_workspace_date 
ON transactions (workspace_id, transaction_date);

-- 2. Status & Date Range (Posted vs Pending)
CREATE INDEX ix_transactions_workspace_status_date 
ON transactions (workspace_id, status, transaction_date);

-- 3. Category Aggregation
CREATE INDEX ix_transactions_workspace_category 
ON transactions (workspace_id, category_id);

-- 4. Single-Account Filter Optimization
CREATE INDEX ix_transactions_account_date 
ON transactions (account_id, transaction_date);

-- 5. Paired Transfer Lookup
CREATE INDEX ix_transactions_transfer_id 
ON transactions (transfer_id);

-- 6. Merchant Name Filtering
CREATE INDEX ix_transactions_merchant_name 
ON transactions (merchant_name);

-- 7. Account Balances and Types
CREATE INDEX ix_accounts_workspace_status 
ON accounts (workspace_id, status);

CREATE INDEX ix_accounts_workspace_type 
ON accounts (workspace_id, account_type);
```

---

## 3. Query Construction Architecture

### 3.1 Single Round-Trip Aggregations
Rather than executing separate database roundtrips to count transactions, sum income, calculate refunds, and compute pending amounts, `get_financial_overview` consolidates all metrics into a single SQL statement using conditional expressions:
```sql
SELECT
  coalesce(sum(CASE WHEN ... THEN amount_paise ELSE 0 END), 0) AS gross_income_paise,
  coalesce(sum(CASE WHEN ... THEN amount_paise ELSE 0 END), 0) AS refunds_paise,
  coalesce(sum(CASE WHEN ... THEN amount_paise ELSE 0 END), 0) AS gross_expenses_paise,
  coalesce(sum(CASE WHEN ... THEN 1 ELSE 0 END), 0) AS transaction_count,
  ...
FROM transactions
WHERE workspace_id = :workspace_id
  AND is_deleted = false
  AND currency = :currency
  AND transaction_date >= :start_date
  AND transaction_date <= :end_date;
```
This achieves minimal CPU and wire overhead, returning an 8-column scalar tuple in a single database flight.

### 3.2 Bounded Spans & DOS Defense
The application service strictly validates that the date span cannot exceed **10 years (3,650 days)**:
```python
if (end_date - start_date).days > 3650:
    raise BusinessRuleViolationError(
        rule_name="DATE_RANGE_EXCEEDED",
        message="Analytics query span cannot exceed 10 years (3650 days)."
    )
```
This prevents malicious or malformed API requests from forcing full-table scans across unbounded historical ranges.
