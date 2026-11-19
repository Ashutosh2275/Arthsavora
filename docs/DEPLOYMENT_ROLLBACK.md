# ARTHSAVORA — Deployment Rollback Procedures

## 1. Rollback Decision Triggers

An immediate production rollback is mandatory under any of the following conditions:
1. **Health Check Failure**: `/api/v1/health/live` or `/api/v1/health/ready` fails for > 60 consecutive seconds post-deploy.
2. **5xx Error Spike**: API gateway 5xx error rate exceeds 1.0% of total traffic over a 3-minute window.
3. **Database Contention**: Database connection pool exhaustion or transaction lock timeouts spike > 5x baseline.
4. **Data Integrity Alarm**: Unbalanced double-entry journal post attempt detected or RLS cross-tenant violation flagged.

## 2. Rollback Execution Runbook

```
                         [ DETECT CRITICAL FAILURE ]
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
[ COMPUTE / FRONTEND ONLY ]                               [ SCHEMA COMPATIBILITY ISSUE ]
1. Re-point ECS Task Definition                           1. Re-point ECS to previous container
   to previous known good tag                             2. If migration was backward-compatible,
2. Purge Cloudflare CDN edge cache                           leave columns in place (Expand phase)
3. Confirm health probes return 200                       3. If destructive migration occurred:
4. Post-incident triage                                      Initiate RDS Point-in-Time Recovery (PITR)
```

### 2.1 Scenario A: Container / Application Code Failure (No Schema Change)
1. **Revert ECS Service**:
   ```bash
   aws ecs update-service \
     --cluster arthsavora-prod \
     --service arthsavora-backend-api \
     --task-definition arthsavora-backend:PREVIOUS_STABLE_REVISION
   ```
2. **Revert Frontend Edge**:
   Re-deploy previous static build artifacts to edge storage and invalidate Cloudflare cache:
   ```bash
   curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -d '{"purge_everything": true}'
   ```
3. **Verify Restoration**:
   Confirm `/api/v1/health/ready` returns HTTP 200 within 30 seconds.

### 2.2 Scenario B: Schema Migration Rollback (Expand/Contract Phase)
Because ARTHSAVORA strictly enforces the **Expand/Contract** database evolution pattern:
- New columns are always added as nullable or with defaults.
- No existing columns are renamed or dropped in the same release that references them.
- Therefore, reverting the application container to the previous version will NOT break database queries, as the previous code simply ignores newly added nullable columns.

### 2.3 Scenario C: Database Recovery (Catastrophic Schema Corruption)
If an unrecoverable data corruption occurs:
1. Immediately place application in Maintenance Mode via Cloudflare edge worker (returns HTTP 503 Maintenance Page).
2. Restore database from pre-deployment snapshot:
   ```bash
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier arthsavora-prod-db \
     --target-db-instance-identifier arthsavora-prod-db-restored \
     --restore-time "2026-11-19T10:00:00Z"
   ```
3. Update `DATABASE_URL` in Secrets Manager to point to restored instance.
4. Verify database readiness and ledger balance.
5. Disable Maintenance Mode at edge.

## 3. Post-Rollback Protocol
- File a P1 Incident Postmortem within 24 hours ([INCIDENT_POSTMORTEM_TEMPLATE.md](file:///d:/Arthsavora/docs/INCIDENT_POSTMORTEM_TEMPLATE.md)).
- Retain container logs and datadog traces for forensic root-cause analysis.
- The failed release tag is marked as `BROKEN` and cannot be redeployed without a subsequent patch.

## 4. Cross-Reference Links
- Release Management: [RELEASE_MANAGEMENT.md](file:///d:/Arthsavora/docs/RELEASE_MANAGEMENT.md)
- Database Change Safety: [DATABASE_CHANGE_SAFETY.md](file:///d:/Arthsavora/docs/DATABASE_CHANGE_SAFETY.md)
- Production Incident Runbook: [PRODUCTION_INCIDENT_RUNBOOK.md](file:///d:/Arthsavora/docs/PRODUCTION_INCIDENT_RUNBOOK.md)
