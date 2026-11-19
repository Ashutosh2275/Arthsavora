# ARTHSAVORA — Background Worker Operations

## 1. Background Processing Architecture

ARTHSAVORA delegates asynchronous, resource-intensive, or delayed tasks to background workers backed by **Redis 7** queues.

```
+-----------------------------------------------------------------------------------+
|                        FASTAPI APPLICATION ENGINE                                 |
+-------------------+---------------------------------------+-----------------------+
                    | Dispatches Asynchronous Task
                    v
+-----------------------------------------------------------------------------------+
|                               REDIS 7 TASK QUEUES                                 |
| - High-Priority Queue (`high`): In-flight notifications, OTP delivery             |
| - Default Queue (`default`): Document OCR extraction, transaction categorization  |
| - Low-Priority Queue (`batch`): Financial reporting rollups, recurring processing |
+-------------------+---------------------------------------+-----------------------+
                    | Consumes with Prefetch
                    v
+-----------------------------------------------------------------------------------+
|                            BACKGROUND WORKER PROCESSES                            |
|                       (Celery / Python Async Workers)                             |
| - Containerized non-root execution                                                |
| - Exponential backoff retry with Dead Letter Queue (DLQ)                          |
| - Idempotency key deduplication                                                   |
+-----------------------------------------------------------------------------------+
```

## 2. Worker Concurrency and Memory Management

- **Worker Runtime**: Python 3.11 with Celery or lightweight AsyncIO background task runner.
- **Concurrency**: 4 worker processes per worker container.
- **Max Tasks Per Child**: `--max-tasks-per-child=1000` (recycles worker child processes periodically to prevent memory fragmentation).
- **Graceful Shutdown**: On `SIGTERM`, workers cease accepting new tasks from Redis and have 30 seconds to finish currently processing tasks before termination.

## 3. Idempotency and Dead Letter Queues (DLQ)

1. **Idempotency**: Every background task carries an idempotency token (`task_id` or `entity_id:version`). Before executing financial updates or external API calls, the worker inspects Redis or PostgreSQL to verify the task has not already completed.
2. **Exponential Backoff**: Transient errors (e.g. rate limit from external bank API, temporary network timeout) retry with backoff: `2^attempt * 5s` (max 5 retries).
3. **Dead Letter Queue (DLQ)**: Tasks that fail 5 consecutive retries are routed to `arthsavora:queue:dlq`.
4. **DLQ Alerting**: A Celery beat or CloudWatch metric alarms if `dlq_length > 0`, notifying on-call engineers for manual inspection.

## 4. Cross-Reference Links
- Scheduled Job Operations: [SCHEDULED_JOB_OPERATIONS.md](file:///d:/Arthsavora/docs/SCHEDULED_JOB_OPERATIONS.md)
- Observability Architecture: [OBSERVABILITY_ARCHITECTURE.md](file:///d:/Arthsavora/docs/OBSERVABILITY_ARCHITECTURE.md)
