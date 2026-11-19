# ARTHSAVORA — Backup, Disaster Recovery & Business Continuity

## 1. Overview & Objectives

ARTHSAVORA stores mission-critical financial ledgers, tax documents, and banking connectivity state. Data loss or extended outages have direct legal and financial consequences.

This standard establishes recovery objectives, backup mechanisms, encryption requirements, and tested restoration procedures.

---

## 2. Recovery Objectives

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **< 1 Hour** | Maximum tolerable data loss. Achieved via continuous Write-Ahead Log (WAL) archiving and hourly snapshot differentials. |
| **Recovery Time Objective (RTO)** | **< 4 Hours** | Maximum tolerable downtime before core financial services and read operations are restored. |

---

## 3. Database Backup Architecture

### 3.1. Relational Database (PostgreSQL 18)
1. **Continuous WAL Archiving (Physical Backups):**
   - PostgreSQL Write-Ahead Logs (WAL) are streamed continuously to encrypted off-site object storage (AWS S3 / Google Cloud Storage).
   - Enables Point-in-Time Recovery (PITR) to any second within the retention window.
2. **Automated Daily Logical Snapshots:**
   - Full logical snapshots generated daily at 02:00 IST using `pg_dump`:
     ```bash
     pg_dump -Fc --no-owner --no-privileges -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER arthsavora > /backups/arthsavora_$(date +%Y%m%d_%H%M%S).dump
     ```
   - Snapshots are compressed with `zstandard` / `gzip` and encrypted using GPG / AES-256 prior to off-site transfer.
3. **Retention Schedule:**
   - Daily snapshots retained for 30 days.
   - Weekly snapshots retained for 12 weeks.
   - Monthly snapshots retained for 8 years (statutory requirement under Indian Companies Act 2013).

### 3.2. Document & Object Storage
- File storage (`storage/documents/`) is mirrored to versioned, geo-redundant cloud object storage with Object Lock (WORM - Write Once, Read Many) to prevent ransomware modification.

---

## 4. Tested Restoration Procedure

A backup is only as good as its tested restore. Restoration must be executed and verified in an isolated staging environment (`arthsavora_restore_test`) without impacting production.

### Step-by-Step Recovery Procedure:
1. **Provision Clean Target Database:**
   ```bash
   createdb -h $RESTORE_HOST -p $RESTORE_PORT -U postgres arthsavora_restore_test
   ```
2. **Execute Restore:**
   ```bash
   pg_restore -h $RESTORE_HOST -p $RESTORE_PORT -U postgres -d arthsavora_restore_test /backups/target_snapshot.dump
   ```
3. **Run Relational Integrity Check:**
   - Verify table counts (86 tables).
   - Verify double-entry ledger balance:
     ```sql
     SELECT
       SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END) AS total_debits,
       SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END) AS total_credits
     FROM journal_lines;
     ```
     Ensure `total_debits = total_credits`.
4. **Run Smoke Test Suite:**
   - Run backend test suite against restored database using `DATABASE_URL` override.
5. **DNS & Traffic Failover:**
   - Once verified, update application connection strings and DNS records to direct traffic to the restored instance.

---

## 5. Security & Access Controls on Backups

- **Zero Unencrypted Backups:** All database dumps and document snapshots are encrypted with AES-256 before leaving the server.
- **Least Privilege:** Backup service accounts possess read-only database dump privileges and write-only bucket privileges. They cannot delete historical backups.
- **Production Isolation:** Production backups containing real financial records are strictly prohibited from being downloaded onto local developer workstations or non-production environments.
