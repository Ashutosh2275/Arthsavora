# ARTHSAVORA — Database Backup and Recovery Operations

## 1. Backup Strategy Architecture

ARTHSAVORA implements a **dual-tier backup topology** combining continuous Write-Ahead Log (WAL) archiving for Point-in-Time Recovery (PITR) with automated full snapshot backups.

```
+-----------------------------------------------------------------------------------+
|                         POSTGRESQL PRIMARY DATASTORE                              |
|                              (AWS RDS Multi-AZ)                                   |
+-------------------+---------------------------------------+-----------------------+
                    | Continuous WAL Stream                 | Daily Snapshot
                    v                                       v
+----------------------------------------+ +----------------------------------------+
|   CONTINUOUS ARCHIVE / WAL STORAGE     | |         AUTOMATED RDS SNAPSHOTS        |
| - Continuous streaming to Amazon S3    | | - Daily full cluster snapshot at 01:30 |
| - 35-day Point-in-Time retention       | |   IST (low traffic window)             |
| - Enables restoration to any second    | | - 35-day retention period              |
| - RPO: < 5 minutes (target < 1 hour)   | | - Encrypted with AWS KMS (AES-256)     |
+----------------------------------------+ +-------------------+--------------------+
                                                               |
                                                               | Cross-Region Copy
                                                               v
                                           +----------------------------------------+
                                           |      DISASTER RECOVERY SNAPSHOTS       |
                                           | - Daily replication to AWS Hyderabad   |
                                           |   (ap-south-2)                         |
                                           | - Geo-redundancy against region loss   |
                                           +----------------------------------------+
```

## 2. Backup Tiers & Retention Schedule

| Tier | Type | Frequency | Retention Window | Storage Target | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PITR WAL** | Continuous WAL Archiving | Continuous (streaming) | 35 Days | Managed S3 | AWS KMS |
| **Daily Full** | RDS Snapshot | Daily at 01:30 IST | 35 Days | Managed EBS / S3 | AWS KMS |
| **Weekly Deep**| RDS Snapshot | Every Sunday 02:00 IST | 180 Days | Cold Storage S3 | AWS KMS |
| **Monthly Archive**| Logical `pg_dump` | 1st of month | 7 Years (Compliance) | S3 Glacier Flexible | GPG + KMS |
| **Pre-Deploy** | Manual Snapshot | Prior to every deploy | 7 Days | Managed EBS | AWS KMS |

## 3. Logical Backup Runbook (`pg_dump`)

For institutional compliance and regulatory off-site escrow:

```bash
# Export compressed, custom-format logical dump with schema and data
pg_dump -h $PG_HOST -p $PG_PORT -U $PG_USER -d arthsavora \
        --format=custom --compress=9 --no-owner --no-privileges \
        --file=arthsavora_backup_$(date +%Y%m%d_%H%M%S).dump

# Encrypt dump with GPG public key
gpg --encrypt --recipient ops@arthsavora.com arthsavora_backup_*.dump

# Upload to restricted compliance vault
aws s3 cp arthsavora_backup_*.dump.gpg s3://arthsavora-compliance-backups/monthly/
```

## 4. Verification and Integrity Testing Schedule

Backups are meaningless without proven restoration. ARTHSAVORA schedules automated monthly disaster restoration dry-runs to an isolated staging instance to verify:
1. Snapshot restores successfully.
2. WAL replay reaches the target timestamp without corruption.
3. Database consistency check passes: `pg_catalog` integrity, foreign keys intact, double-entry ledger debit/credit balances match to zero difference.

## 5. Cross-Reference Links
- Disaster Recovery Runbook: [DISASTER_RECOVERY_RUNBOOK.md](file:///d:/Arthsavora/docs/DISASTER_RECOVERY_RUNBOOK.md)
- Recovery Test Results: [RECOVERY_TEST_RESULTS.md](file:///d:/Arthsavora/docs/RECOVERY_TEST_RESULTS.md)
- RPO & RTO Policy: [RPO_RTO_POLICY.md](file:///d:/Arthsavora/docs/RPO_RTO_POLICY.md)
