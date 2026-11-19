# ARTHSAVORA — Disaster Recovery Runbook

## 1. Disaster Recovery Classification

| Disaster Severity | Scenario | Declared By | Target RTO | Target RPO |
| :--- | :--- | :--- | :--- | :--- |
| **P1 - Data Corruption** | Erroneous bulk update / SQL injection | Head of Engineering | < 2 Hours | < 15 Minutes |
| **P1 - Primary DB Outage**| AWS Mumbai AZ failure / RDS hardware fault | Lead SRE | < 30 Minutes | < 1 Minute (Sync) |
| **P0 - Regional Outage** | Complete AWS Mumbai (`ap-south-1`) failure | CTO / Incident Commander | < 4 Hours | < 1 Hour |

## 2. Recovery Protocols

### 2.1 Scenario 1: Point-in-Time Recovery (PITR) to Remediate Data Corruption
When data is corrupted at timestamp `T_corrupt` (e.g., `2026-11-19T14:32:00Z`):

1. **Halt Application Writes**:
   Put application in maintenance mode at Cloudflare edge worker (returns HTTP 503).
2. **Execute PITR to `T_corrupt - 60s`**:
   ```bash
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier arthsavora-prod-db \
     --target-db-instance-identifier arthsavora-prod-restored \
     --restore-time "2026-11-19T14:31:00Z" \
     --db-subnet-group-name arthsavora-db-subnet-group \
     --vpc-security-group-ids sg-0123456789abcdef0 \
     --publicly-accessible false
   ```
3. **Run Integrity Verification**:
   Execute ledger verification query:
   ```sql
   SELECT SUM(debit_amount) - SUM(credit_amount) AS ledger_imbalance FROM journal_entries;
   ```
   Must return exactly `0.00`.
4. **Switch Traffic**:
   Update `DATABASE_URL` in AWS Secrets Manager and restart ECS backend services.
5. **Lift Maintenance Mode**.

### 2.2 Scenario 2: Multi-AZ Automated Database Failover
AWS RDS Multi-AZ automatically detects primary node failure (loss of network, disk failure) and flips DNS to the synchronous standby replica within 60–120 seconds.
- Application pool handles retry automatically with backoff.
- On-call engineer monitors CloudWatch metric `DatabaseConnections` and confirms connection restoration.

### 2.3 Scenario 3: Regional Failover to AWS Hyderabad (`ap-south-2`)
1. **Activate Secondary VPC**:
   Launch ECS tasks in `ap-south-2` targeting the replicated RDS snapshot.
2. **Promote Replicated Snapshot**:
   ```bash
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier arthsavora-dr-db \
     --db-snapshot-identifier arn:aws:rds:ap-south-2:123456789012:snapshot:arthsavora-cross-region-latest \
     --region ap-south-2
   ```
3. **Update Global DNS**:
   In Cloudflare DNS, update the origin IP/CNAME for `api.arthsavora.com` to point to the `ap-south-2` Application Load Balancer.
4. **Notify Stakeholders**:
   Publish incident update to status page (`status.arthsavora.com`).

## 3. Communication and Escalation Chain
1. **Incident Commander (IC)**: Leads triage, declares disaster level.
2. **Operations Lead**: Executes restoration CLI commands.
3. **Communications Lead**: Updates status page and customer notifications every 30 minutes.

## 4. Cross-Reference Links
- Backup Operations: [BACKUP_OPERATIONS.md](file:///d:/Arthsavora/docs/BACKUP_OPERATIONS.md)
- Recovery Test Results: [RECOVERY_TEST_RESULTS.md](file:///d:/Arthsavora/docs/RECOVERY_TEST_RESULTS.md)
- RPO & RTO Policy: [RPO_RTO_POLICY.md](file:///d:/Arthsavora/docs/RPO_RTO_POLICY.md)
