# ARTHSAVORA — Production Incident Management Runbook

## 1. Incident Lifecycle

When a production outage, security event, or data anomaly occurs, engineers follow the four-phase incident management protocol:

```
[ 1. TRIAGE & ASSIGN ]  -->  [ 2. MITIGATE & RESTORE ]  -->  [ 3. RESOLVE & VERIFY ]  -->  [ 4. POSTMORTEM ]
- Assign Incident Cmdr        - Halt bleeding / rollback      - Synthetic probe check       - Root-cause analysis
- Assess Severity             - Drain bad containers          - Customer status update      - Corrective action items
- Open incident channel       - Switch to DR / Failover       - Archive audit logs          - Preventive safeguards
```

## 2. Roles & Responsibilities

- **Incident Commander (IC)**: Has absolute operational authority. Assigns tasks, oversees communication, and coordinates mitigation actions.
- **Operations Lead**: Executes CLI diagnostics, database queries, and deployment commands.
- **Communications Lead**: Maintains `status.arthsavora.com` updates and handles customer/stakeholder inquiries.

## 3. High-Priority Failure Mode Playbooks

### 3.1 Playbook A: 503 Service Unavailable / Database Down
1. Check RDS status:
   ```bash
   aws rds describe-db-instances --db-instance-identifier arthsavora-prod-db --query 'DBInstances[0].DBInstanceStatus'
   ```
2. If RDS is in reboot/failover, wait for Multi-AZ promotion (approx. 60–90 seconds).
3. If RDS is hung, trigger forced failover:
   ```bash
   aws rds reboot-db-instance --db-instance-identifier arthsavora-prod-db --force-failover
   ```
4. Check connection pool exhaustion on backend containers.

### 3.2 Playbook B: High API 5xx Spike Post-Deployment
1. Immediately review ECS service deployments.
2. If error spike coincides with a new deployment, execute **Scenario A Rollback** ([DEPLOYMENT_ROLLBACK.md](file:///d:/Arthsavora/docs/DEPLOYMENT_ROLLBACK.md)).
3. Revert ECS Task Definition to previous revision tag.
4. Purge Cloudflare CDN edge cache.

### 3.3 Playbook C: Memory Leak / Container CrashLoop
1. Inspect container exit code (`137` = OOMKilled).
2. Double container task memory allocation temporarily in ECS service configuration (from 2048 MB to 4096 MB).
3. Capture heap snapshot or memory profile if process is still alive.
4. Drain and restart leaking container tasks.

## 4. Resolution and Hand-off

- Incident is marked **RESOLVED** only when `/api/v1/health/ready` returns 200, error rates fall below 0.05%, and all primary workflows (Auth, Transactions, Ledger) pass synthetic verification for 15 consecutive minutes.
- The Incident Commander schedules the blameless postmortem within 48 hours.

## 5. Cross-Reference Links
- Alerting & Escalation: [ALERTING_AND_ESCALATION.md](file:///d:/Arthsavora/docs/ALERTING_AND_ESCALATION.md)
- Deployment Rollback: [DEPLOYMENT_ROLLBACK.md](file:///d:/Arthsavora/docs/DEPLOYMENT_ROLLBACK.md)
- Incident Postmortem Template: [INCIDENT_POSTMORTEM_TEMPLATE.md](file:///d:/Arthsavora/docs/INCIDENT_POSTMORTEM_TEMPLATE.md)
