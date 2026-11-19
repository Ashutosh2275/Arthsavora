# ARTHSAVORA — Operational Monitoring Framework

## 1. Monitoring Scope

The ARTHSAVORA operational monitoring infrastructure monitors four primary domains:
1. **Network & Edge**: Cloudflare requests, WAF blocks, SSL certificate validity, DNS latency.
2. **Compute**: ECS Fargate container CPU utilization, memory RSS, task count, restart counts.
3. **Storage & Data**: RDS CPU, storage space, replication lag, connection count, IOPS, deadlocks.
4. **Application Health**: Synthetic probe status, error rates, p95/p99 latency, queue depth.

## 2. Dashboard Layout (Single-Pane-of-Glass)

```
+-----------------------------------------------------------------------------------+
|                        ARTHSAVORA OPERATIONS DASHBOARD                            |
+-----------------------------------------------------------------------------------+
| [ WAF Request Rate ]       [ API 5xx Error Rate ]      [ p95 Latency (ms) ]       |
| 1,240 req/min              0.02% (Target < 0.1%)       48ms (Target < 200ms)      |
+-----------------------------------------------------------------------------------+
| [ PostgreSQL CPU ]         [ Active DB Connections ]   [ Replica Lag (sec) ]      |
| 18% (Target < 70%)         14 / 100 max                0.00s (Synchronous)        |
+-----------------------------------------------------------------------------------+
| [ Redis Memory RSS ]       [ Background Queue Depth ]  [ Double-Entry Invariants] |
| 112 MB / 512 MB            0 pending items             100% Balanced (0 alerts)   |
+-----------------------------------------------------------------------------------+
```

## 3. Synthetic Blackbox Probing

- An external monitoring service (e.g., Better Uptime or Datadog Synthetic Monitoring) executes external HTTP GET requests against:
  - `https://app.arthsavora.com/` (expecting 200 and `<div id="root">`)
  - `https://api.arthsavora.com/api/v1/health/live` (expecting 200 `< 500ms`)
  - `https://api.arthsavora.com/api/v1/health/ready` (expecting 200 `< 1000ms`)
- Frequency: Every 60 seconds from Mumbai, Singapore, and Frankfurt.

## 4. Cross-Reference Links
- Observability Architecture: [OBSERVABILITY_ARCHITECTURE.md](file:///d:/Arthsavora/docs/OBSERVABILITY_ARCHITECTURE.md)
- Alerting and Escalation: [ALERTING_AND_ESCALATION.md](file:///d:/Arthsavora/docs/ALERTING_AND_ESCALATION.md)
- Production Incident Runbook: [PRODUCTION_INCIDENT_RUNBOOK.md](file:///d:/Arthsavora/docs/PRODUCTION_INCIDENT_RUNBOOK.md)
