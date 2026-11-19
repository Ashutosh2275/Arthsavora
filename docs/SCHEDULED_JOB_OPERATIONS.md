# ARTHSAVORA — Scheduled Job and Cron Operations

## 1. Recurring Job Catalog

Scheduled jobs in ARTHSAVORA are coordinated via distributed scheduler with Redis locks or AWS EventBridge scheduled tasks.

| Job Name | Schedule (IST) | Target Queue | Purpose | Timeout |
| :--- | :--- | :--- | :--- | :--- |
| `reconcile_recurring_commitments` | Daily at 00:30 | `default` | Evaluates recurring definitions, creates expected occurrences | 15 mins |
| `sync_account_aggregator_feeds` | Daily at 02:00 | `batch` | Polls Account Aggregators for consented bank updates | 30 mins |
| `detect_financial_anomalies` | Daily at 03:00 | `default` | Scans prior 24h transactions for anomaly patterns | 20 mins |
| `generate_cashflow_forecasts` | Weekly (Sun 04:00) | `batch` | Precomputes 30/60/90-day cashflow models | 45 mins |
| `cleanup_expired_tokens` | Hourly (at :15) | `high` | Purges expired token JTIs from Redis revocation registry | 5 mins |
| `database_vacuum_analyze` | Daily at 01:30 | N/A (RDS) | Database autovacuum and statistics recalculation | 60 mins |

## 2. Distributed Locking for Scheduled Tasks

To prevent overlapping execution in multi-container environments, all scheduled jobs acquire a distributed lock via Redis:

```python
async with redis_lock("job:reconcile_recurring_commitments", timeout=900):
    await execute_reconciliation()
```
- If a job is already executing on another container, secondary attempts log an info message and exit cleanly without duplicate execution.

## 3. Failure Monitoring and Retries
- Missed or failed cron executions are tracked in Prometheus/CloudWatch.
- If a cron job fails, it automatically emits an event to the `SEV-3` Slack channel.

## 4. Cross-Reference Links
- Background Worker Operations: [BACKGROUND_WORKER_OPERATIONS.md](file:///d:/Arthsavora/docs/BACKGROUND_WORKER_OPERATIONS.md)
- Operational Monitoring: [OPERATIONAL_MONITORING.md](file:///d:/Arthsavora/docs/OPERATIONAL_MONITORING.md)
