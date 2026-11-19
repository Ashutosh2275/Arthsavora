# ARTHSAVORA — Recovery Point Objective (RPO) and Recovery Time Objective (RTO) Policy

## 1. Executive Summary & Policy Scope

As an institutional commercial financial platform handling general ledger accounting, payment reconciliations, GST compliance records, and family/business finances, ARTHSAVORA establishes non-negotiable **Service Level Objectives (SLOs)** for business continuity and disaster recovery.

## 2. Definitive RPO & RTO Targets

| System Component | Disaster Tier | Target RPO (Max Data Loss) | Target RTO (Max Downtime) | Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL Primary** | Node Outage | **0 Seconds** (Sync) | **< 2 Minutes** | AWS RDS Multi-AZ Automatic Failover |
| **PostgreSQL Primary** | Data Corruption | **< 15 Minutes** | **< 2 Hours** | S3 WAL Continuous Point-in-Time Recovery |
| **PostgreSQL Primary** | Regional Catastrophe | **< 1 Hour** | **< 4 Hours** | Cross-Region Snapshot Replication (`ap-south-2`)|
| **Backend API Compute**| Container Crash | **0 Seconds** | **< 15 Seconds** | ECS Task Auto-Restart & Health Check |
| **Redis Cache** | Node Loss | **< 1 Second** (AOF) | **< 1 Minute** | ElastiCache Multi-AZ Cluster Failover |
| **Document Storage (S3)**| Storage Node Loss | **0 Seconds** | **< 1 Minute** | S3 Standard 99.999999999% (11 9's) Durability |
| **Edge CDN & DNS** | Edge Point of Presence | **0 Seconds** | **< 30 Seconds** | Cloudflare Anycast Automatic BGP Routing |

## 3. Financial Integrity Compliance Invariant

- **Zero Ledger Data Loss Invariant**: No disaster recovery scenario is permitted to compromise the mathematical balance of the double-entry general ledger.
- If a point-in-time restoration causes unbalanced transactions due to midway WAL truncations, the recovery runner MUST automatically rollback the incomplete batch or isolate it into an administrative quarantine schema for audit review.

## 4. Audit and Compliance Review

- This policy is reviewed quarterly by the CTO and Chief Information Security Officer (CISO).
- Drill execution results are archived in [RECOVERY_TEST_RESULTS.md](file:///d:/Arthsavora/docs/RECOVERY_TEST_RESULTS.md) for regulatory audit by Indian authorities (RBI / SEBI).

## 5. Cross-Reference Links
- Backup Operations: [BACKUP_OPERATIONS.md](file:///d:/Arthsavora/docs/BACKUP_OPERATIONS.md)
- Disaster Recovery Runbook: [DISASTER_RECOVERY_RUNBOOK.md](file:///d:/Arthsavora/docs/DISASTER_RECOVERY_RUNBOOK.md)
- Recovery Test Results: [RECOVERY_TEST_RESULTS.md](file:///d:/Arthsavora/docs/RECOVERY_TEST_RESULTS.md)
