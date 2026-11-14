# ARTHSAVORA Notification Retention Policy & Lifecycle Management

## 1. Executive Summary

As a high-volume commercial FinTech platform, ARTHSAVORA processes alerts across millions of financial events. Maintaining an unbounded notification history introduces storage bloat, degrades database query performance, and increases compliance liability.

This document defines the data retention tiers, automated cleanup routines, and partition-ready lifecycle policies governing the `notifications` and `notification_deliveries` tables.

---

## 2. Notification Data Lifecycle Tiers

| Retention Tier | State / Criteria | Retention Window | Storage Action |
| :--- | :--- | :--- | :--- |
| **Active Unread** | `is_read = FALSE`, `is_archived = FALSE` | Up to 180 Days | Maintained in hot storage; surfaced in notification badge. |
| **Read Notifications** | `is_read = TRUE`, `is_archived = FALSE` | 90 Days | Retained in hot storage for user review, then transitioned to archive. |
| **Archived Notifications**| `is_archived = TRUE` | 365 Days | Kept in warm partition; retrievable via search or export. |
| **Security Alerts** | `category = 'security'` | 7 Years (Audit) | Excluded from automated pruning; preserved for compliance. |
| **Channel Deliveries** | Records in `notification_deliveries` | 30 Days | Retained for delivery confirmation and debugging, then purged. |
| **Stale Push Subscriptions**| Expired / 410 Gone push tokens | Immediate on failure | Deactivated or deleted upon provider 404/410 response. |

---

## 3. Database Indexing & Partitioning Strategy

### 3.1 Hot-Storage Indexes
The `notifications` table is indexed to support high-throughput filtering by user, read status, and timestamp:

```sql
CREATE INDEX ix_notifications_user_unread 
ON notifications (recipient_user_id, is_read, created_at DESC) 
WHERE is_read = FALSE;

CREATE INDEX ix_notifications_user_created 
ON notifications (recipient_user_id, created_at DESC);

CREATE INDEX ix_notifications_dedup 
ON notifications (recipient_user_id, deduplication_key) 
WHERE deduplication_key IS NOT NULL;
```

### 3.2 Time-Series Table Partitioning (Production Scale)
At enterprise scale, `notifications` and `notification_deliveries` are structured for PostgreSQL native declarative partitioning by range (`created_at`):

```sql
-- Partitioning scheme for notifications
CREATE TABLE notifications_partitioned (
    id UUID NOT NULL,
    recipient_user_id UUID NOT NULL,
    category VARCHAR(32) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    ...
) PARTITION BY RANGE (created_at);

-- Monthly partition creation
CREATE TABLE notifications_y2026m11 PARTITION OF notifications_partitioned
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
```

Partitions older than the statutory retention period (e.g., 365 days) can be detached and archived to cold object storage (e.g., S3/GCS parquet) with zero locking impact on active transactions.

---

## 4. Automated Cleanup & Archival Routine

A background cleanup routine (`cleanup_expired_notifications_worker`) executes during off-peak hours:

```python
async def cleanup_expired_notifications(db: AsyncSession, dry_run: bool = False) -> int:
    cutoff_90d = datetime.now(timezone.utc) - timedelta(days=90)
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    
    # 1. Archive read notifications older than 90 days (excluding security events)
    stmt_archive = (
        update(Notification)
        .where(
            Notification.is_read.is_(True),
            Notification.is_archived.is_(False),
            Notification.category != NotificationCategory.SECURITY.value,
            Notification.created_at < cutoff_90d,
        )
        .values(is_archived=True)
    )
    await db.execute(stmt_archive)

    # 2. Purge delivery logs older than 30 days
    stmt_purge_deliveries = (
        delete(NotificationDelivery)
        .where(NotificationDelivery.created_at < cutoff_30d)
    )
    await db.execute(stmt_purge_deliveries)

    await db.commit()
```

---

## 5. User Data Deletion & Privacy Compliance

In accordance with applicable privacy regulations (DPDP Act India / GDPR):
- When a user deletes their account or requests data erasure, all associated records in `notifications`, `notification_deliveries`, `notification_preferences`, and `push_subscriptions` are deleted via cascading foreign key constraints (`ondelete="CASCADE"`).
- Audit-mandated security incident logs are scrubbed of personally identifiable information (PII) and pseudonymized in compliance with institutional requirements.
