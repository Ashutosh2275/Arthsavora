# ARTHSAVORA — Incident Postmortem Template

*Note: ARTHSAVORA conducts strictly **blameless postmortems**. The objective is to identify systemic vulnerabilities, process gaps, and engineering improvements.*

---

## Incident Summary

| Field | Detail |
| :--- | :--- |
| **Incident Title** | [e.g., 2026-11-19: Database Connection Pool Exhaustion during Month-End] |
| **Severity** | [SEV-1 / SEV-2 / SEV-3] |
| **Date & Time (IST)**| [YYYY-MM-DD HH:MM IST] |
| **Duration** | [e.g., 24 minutes] |
| **Incident Commander**| [Name] |
| **Impact Summary** | [e.g., ~1,400 user requests failed with HTTP 503; 0 ledger records corrupted] |

---

## Timeline of Events (All times in IST)

- **11:02** - Automated alert `EndpointReadinessDown` fires in PagerDuty.
- **11:05** - On-Call Engineer acknowledges alert and initiates triage.
- **11:08** - Incident Commander declares SEV-1 incident; opens Slack channel `#inc-20261119`.
- **11:12** - Operations Lead identifies 100 active connections in `pg_stat_activity` stuck in uncommitted state.
- **11:15** - Mitigation: Backend container tasks recycled, idle transaction timeout enforced.
- **11:22** - Readiness probes return HTTP 200 across all zones.
- **11:26** - Incident Commander declares incident MITIGATED.
- **11:45** - 15-minute stable operating window observed; incident declared RESOLVED.

---

## Root Cause Analysis (5 Whys)

1. **Why did the API return HTTP 503?**
   - The `/ready` probe and user transactions timed out waiting for an available PostgreSQL connection.
2. **Why were no database connections available?**
   - The connection pool was exhausted with 100 active connections leased by worker threads.
3. **Why were the connections leased for so long?**
   - An unindexed query in the financial reporting service caused sequential table scans.
4. **Why was the query unindexed?**
   - A recent migration omitted the concurrent composite index on `(workspace_id, transaction_date)`.
5. **Why was the missing index not caught in CI?**
   - CI runs on small test datasets where table scans complete in < 5ms.

---

## Action Items and Corrective Safeguards

| Action Item | Type | Owner | Target Date | Status |
| :--- | :--- | :--- | :--- | :--- |
| Add concurrent composite index on `transactions(workspace_id, transaction_date)` | Prevention | Database Lead | 2026-11-20 | Completed |
| Add query latency regression check in CI with synthetic 100k row dataset | Detection | SRE Lead | 2026-11-25 | Open |
| Lower `idle_in_transaction_session_timeout` to 30 seconds | Mitigation | Database Lead | 2026-11-20 | Completed |
| Tune pool sizing to limit max connections per container to 20 | Mitigation | Backend Lead | 2026-11-21 | Open |

---

## Sign-Off
- **Incident Commander**: ______________________
- **Lead Database Architect**: ______________________
- **Head of Engineering / CTO**: ______________________
