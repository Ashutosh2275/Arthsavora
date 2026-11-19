# ARTHSAVORA — Metrics and Distributed Tracing Framework

## 1. Key Performance Indicators (RED Metrics)

ARTHSAVORA instruments the **RED (Rate, Errors, Duration)** methodology across all API endpoints:

- **Rate**: Requests per second (RPS) partitioned by HTTP method, route, and status code.
- **Errors**: Number of failed requests per second (4xx client errors, 5xx server errors).
- **Duration**: Distribution of request latencies (p50, p90, p95, p99).

## 2. Standard Metric Definitions

### 2.1 Application & System Metrics
| Metric Name | Type | Description | Alert Threshold |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | Total incoming requests | N/A |
| `http_request_duration_seconds`| Histogram | Latency distribution | p95 > 500ms, p99 > 1500ms |
| `db_connection_pool_active` | Gauge | Active leased DB connections | > 80% pool capacity |
| `db_connection_pool_waiting`| Gauge | Requests blocked waiting for DB conn | > 5 waiting threads |
| `redis_command_latency_seconds`| Histogram| Latency of cache operations | p95 > 20ms |
| `auth_token_revocations_total`| Counter | Revoked JWT tokens added to blacklist | Spike > 50/min |

### 2.2 Financial Integrity Business Metrics
| Metric Name | Type | Description | Target |
| :--- | :--- | :--- | :--- |
| `ledger_journal_posts_total` | Counter | Committed double-entry journal batches | Monitored |
| `ledger_unbalanced_attempts` | Counter | Blocked attempts to post unbalanced debits/credits | **MUST BE 0** |
| `account_aggregator_syncs_total`| Counter | Completed bank sync synchronizations | Monitored |
| `anomaly_detections_total` | Counter | Identified financial anomalies | Monitored |

## 3. Distributed Tracing & W3C TraceContext

When APM (Datadog or OpenTelemetry) is active:
- Standard W3C headers (`traceparent`, `tracestate`) are parsed on intake.
- Spans are generated for:
  - Top-level HTTP Request (`fastapi.request`)
  - Database Query Execution (`sqlalchemy.execute`)
  - Cache Operations (`redis.command`)
  - AI Assistant Invocations (`gemini.generate_content`)
  - Document OCR Processing (`tesseract.image_to_string`)

## 4. Cross-Reference Links
- Observability Architecture: [OBSERVABILITY_ARCHITECTURE.md](file:///d:/Arthsavora/docs/OBSERVABILITY_ARCHITECTURE.md)
- Operational Monitoring: [OPERATIONAL_MONITORING.md](file:///d:/Arthsavora/docs/OPERATIONAL_MONITORING.md)
- Health Check Standard: [HEALTH_CHECK_STANDARD.md](file:///d:/Arthsavora/docs/HEALTH_CHECK_STANDARD.md)
