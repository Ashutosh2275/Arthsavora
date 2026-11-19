# ARTHSAVORA — Observability Architecture

## 1. Observability Pillars

ARTHSAVORA implements a unified, three-pillar observability framework across logs, metrics, and traces. The architecture balances deep operational visibility with cost-efficiency and strict financial privacy.

```
+-----------------------------------------------------------------------------------+
|                           OBSERVABILITY FRAMEWORK                                 |
+-------------------+---------------------------------------+-----------------------+
|  STRUCTURED LOGS  |           REAL-TIME METRICS           |   DISTRIBUTED TRACES  |
| - JSON Formatter  | - Prometheus / CloudWatch Metrics     | - OpenTelemetry / APM |
| - Automated PII   | - System Saturation (CPU, RAM, Conn)  | - W3C TraceContext    |
|   Redaction Engine| - RED Metrics (Rate, Errors, Duration)| - Request Correlation |
| - Correlation ID  | - Financial Health & Invariant Drift  |   Header Propagation  |
+-------------------+---------------------------------------+-----------------------+
```

## 2. Request Correlation & Context Propagation

Every incoming HTTP request is assigned a unique correlation ID by `app/api/middleware/audit.py`:
- Ingests `X-Request-ID` or `X-Correlation-ID` from client, or generates UUIDv4.
- Injects correlation ID into the response headers (`X-Request-ID`).
- Attaches correlation ID to the logging context so that every database query, background task, and audit log line emitted during the request life cycle shares the same identifier.

## 3. High-Watermark Telemetry Streams

1. **Structured Log Stream**: Single-line JSON emitted to stdout, scraped by AWS CloudWatch Logs Agent or Datadog Daemon.
2. **System & Business Metrics**:
   - HTTP Latency (p50, p95, p99).
   - HTTP 4xx / 5xx error counters.
   - Active PostgreSQL connections and transaction duration.
   - Redis cache hit/miss ratio.
   - Financial ledger post volumes and anomaly detection triggers.
3. **Synthetic Probes**: Automated uptime pings targeting `/api/v1/health/live` and `/api/v1/health/ready` every 30 seconds from multiple geographic vantage points.

## 4. Cross-Reference Links
- Structured Logging Standard: [STRUCTURED_LOGGING_STANDARD.md](file:///d:/Arthsavora/docs/STRUCTURED_LOGGING_STANDARD.md)
- Metrics & Tracing: [METRICS_AND_TRACING.md](file:///d:/Arthsavora/docs/METRICS_AND_TRACING.md)
- Health Check Standard: [HEALTH_CHECK_STANDARD.md](file:///d:/Arthsavora/docs/HEALTH_CHECK_STANDARD.md)
