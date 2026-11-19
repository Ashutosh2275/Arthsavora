# Final Production Operations Runbook

## 1. Daily Operations and Service Health

This runbook guides system administrators and SRE engineers through day-to-day operations, incident triage, and maintenance of the ARTHSAVORA production platform.

---

## 2. Standard Service Management Commands

### 2.1 Checking Health and Probes
```bash
# Check Backend Process Liveness (Sub-5ms in-memory check)
curl -i http://localhost:8000/api/v1/health/live

# Check Database Connectivity and Readiness
curl -i http://localhost:8000/api/v1/health/ready

# Check Frontend Nginx Reverse Proxy
curl -i http://localhost:80/nginx-health
```

### 2.2 Inspecting Structured Application Logs
```bash
# Stream JSON structured logs formatted with request_id and level
docker compose logs -f backend | jq .

# Filter for error-level logs only
docker compose logs backend | jq 'select(.level == "ERROR")'
```

### 2.3 Running Database Migrations Manually
```bash
# Execute safe migration with PostgreSQL advisory lock
uv run python backend/scripts/run_migrations.py
```

---

## 3. Incident Triage Procedures

### 3.1 High Database CPU / Pool Exhaustion
1. Query active pg_stat_activity connections:
   ```sql
   SELECT pid, now() - query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle' ORDER BY duration DESC;
   ```
2. Terminate long-running rogue queries:
   ```sql
   SELECT pg_cancel_backend(pid);
   ```

### 3.2 Redis Cache Disconnection
1. Confirm Redis container status: `docker ps | grep redis`.
2. Backend will log warnings and fallback to PostgreSQL session lookups.
3. Restart Redis: `docker compose restart redis`.
