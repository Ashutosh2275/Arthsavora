# Post-Launch Maintenance and Capacity Plan

## 1. Ongoing Maintenance Cadence

Following the initial beta and production rollout, ARTHSAVORA adheres to a disciplined operational maintenance schedule.

| Cadence | Operational Activity | Responsible Role | Verification Method |
|---|---|---|---|
| **Daily** | Review API error rates, slow queries, and dead-letter queues | SRE / On-Call Engineer | Datadog / Grafana Dashboard |
| **Weekly** | Automated dependency security scan & Dependabot PR reviews | Security Officer | `pip-audit`, `pnpm audit` |
| **Weekly** | Database backup integrity verification (automated test restore) | Database Administrator | Sandbox restore script |
| **Monthly** | Performance benchmarking & database index optimization | Backend Lead | `EXPLAIN ANALYZE` on top 10 queries |
| **Quarterly** | Disaster recovery simulation & secrets rotation drill | Security & DevOps Leads | Failover runbook test |

---

## 2. Maintenance Windows and Change Advisory

- **Standard Maintenance Window**: Sundays, 02:00 AM – 04:00 AM IST (Period of lowest financial transaction activity).
- **Zero-Downtime Releases**: Application code updates and non-breaking database column additions are deployed without downtime during working hours.
- **Breaking DDL Changes**: Complex table refactoring or partition adjustments are restricted to standard maintenance windows with advance user notification.

---

## 3. Capacity and Growth Thresholds

| Resource | Current Baseline | Scaling Trigger Threshold | Scaling Action |
|---|---|---|---|
| **Database Storage** | 20 GB SSD | 75% utilization | Automated storage volume expansion (+50 GB) |
| **Database Connections** | Max 100 pooled | 80 active connections | Increase pool size or deploy PgBouncer |
| **Backend CPU** | 15% average | Sustained > 70% over 5m | Horizontal pod autoscaling (1 to 5 replicas) |
| **Redis Memory** | 128 MB | 80% of maxmemory | Evict volatile keys (allkeys-lru) |
