# ARTHSAVORA — Alerting Rules and Escalation Matrix

## 1. Severity Classifications

| Severity | Definition | Response SLA | Notification Channels |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core outage, database down, data corruption, balanced ledger breach | **< 15 Minutes** | PagerDuty / Opsgenie phone call + SMS + #prod-incidents Slack |
| **SEV-2 (High)** | Degraded service (e.g. AI assistant failing, high 5xx error rate > 2%) | **< 30 Minutes** | PagerDuty push notification + Slack #prod-alerts |
| **SEV-3 (Medium)** | Non-blocking issues, high disk utilization (>80%), single task restart | **< 4 Hours** | Slack #prod-alerts |
| **SEV-4 (Low)** | Informational notices, routine SSL renewal, scheduled backup completed | **Next Business Day**| Slack #ops-log |

## 2. Definitive Alerting Rules

### 2.1 Critical (SEV-1) Alerts
1. `EndpointReadinessDown`:
   - Condition: `/api/v1/health/ready` returns non-200 for 2 consecutive minutes.
   - Action: Automated failover check, page On-Call Engineer.
2. `LedgerImbalanceDetected`:
   - Condition: `ledger_unbalanced_attempts > 0`.
   - Action: Immediate P1 freeze on ledger postings, alert Lead Database Architect.
3. `DatabaseConnectionExhaustion`:
   - Condition: Active PostgreSQL connections > 90% of max allowed for 3 minutes.
   - Action: Alert On-Call Engineer, investigate pool leak.

### 2.2 High (SEV-2) Alerts
1. `HighAPIErrorRate`:
   - Condition: 5xx error percentage > 1.0% over 5 minutes.
   - Action: Check recent deployment tag, trigger canary rollback if deployment was recent.
2. `ElevatedAPILatency`:
   - Condition: HTTP p95 latency > 1000ms over 5 minutes.
   - Action: Check container CPU saturation and database slow query logs.
3. `RedisDown`:
   - Condition: Redis ping failure > 60 seconds.
   - Action: Check Redis memory and connection pool.

## 3. Escalation Chain

```
               [ Alert Fires: SEV-1 or SEV-2 ]
                               |
                               v
               [ Primary On-Call Engineer (0 - 15m) ]
                               |
              (Unacknowledged after 15 minutes)
                               v
              [ Secondary On-Call SRE (15 - 30m) ]
                               |
              (Unacknowledged after 30 minutes)
                               v
           [ Engineering Lead / CTO (30m+) ]
```

## 4. Cross-Reference Links
- Operational Monitoring: [OPERATIONAL_MONITORING.md](file:///d:/Arthsavora/docs/OPERATIONAL_MONITORING.md)
- Production Incident Runbook: [PRODUCTION_INCIDENT_RUNBOOK.md](file:///d:/Arthsavora/docs/PRODUCTION_INCIDENT_RUNBOOK.md)
- Incident Postmortem Template: [INCIDENT_POSTMORTEM_TEMPLATE.md](file:///d:/Arthsavora/docs/INCIDENT_POSTMORTEM_TEMPLATE.md)
