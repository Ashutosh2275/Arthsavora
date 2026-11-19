# Final Operational Handover Document

## 1. Operational Ownership and Architecture

This document transfers day-to-day operational procedures to the ongoing Site Reliability Engineering (SRE) and DevOps teams.

---

## 2. Standard Production Operations

### 2.1 Starting the Production Stack Locally / On-Premise
```bash
# Bring up full containerized environment
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

### 2.2 Health Probes and Monitoring Endpoints
- **Liveness Probe**: `http://localhost:8000/api/v1/health/live` (In-memory, sub-5ms).
- **Readiness Probe**: `http://localhost:8000/api/v1/health/ready` (Validates database connection, 2s timeout).
- **Frontend Nginx Probe**: `http://localhost:80/nginx-health` (HTTP 200).

### 2.3 Automated Database Migrations
Migrations must always be executed through the advisory lock wrapper to avoid multi-instance deployment collisions:
```bash
docker compose exec backend uv run python backend/scripts/run_migrations.py
```

---

## 3. Disaster Recovery and Backup Operations

- **Automated Nightly Backups**: Handled via managed database snapshot or `pg_dump`:
  ```bash
  pg_dump -U postgres -d arthsavora -Fc -f /backups/arthsavora_$(date +%Y%m%d_%H%M%S).dump
  ```
- **Target RPO**: $\le 1\text{ hour}$ via WAL archiving.
- **Target RTO**: $\le 15\text{ minutes}$ via automated container replacement and PITR.
- **Rollback Runbook**: Documented in [RELEASE_ROLLBACK_VALIDATION.md](file:///d:/Arthsavora/docs/RELEASE_ROLLBACK_VALIDATION.md).
