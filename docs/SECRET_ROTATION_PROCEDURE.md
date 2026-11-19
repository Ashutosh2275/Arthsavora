# ARTHSAVORA — Secret Rotation Procedure

## 1. Scope and Frequency

This procedure outlines the zero-downtime rotation protocol for all cryptographic secrets and external credentials powering ARTHSAVORA.

| Secret Class | Target | Rotation Frequency | Rotation Strategy |
| :--- | :--- | :--- | :--- |
| **Database Credentials** | PostgreSQL application user password | 90 days / on event | Dual-user rotation with zero downtime |
| **JWT Signing Key** | `SECRET_KEY` | 180 days / on event | Staged key rollover (Active + Verification fallback) |
| **Redis Auth Token** | Redis cluster auth token | 90 days | Multi-auth rolling update |
| **AI & Third-Party APIs**| `GEMINI_API_KEY`, Supabase keys | 180 days / on leak | Parallel credential provisioning |

## 2. Step-by-Step Rotation Runbooks

### 2.1 Database Credential Rotation (PostgreSQL)
1. **Provision Secondary User**:
   ```sql
   CREATE USER arthsavora_app_v2 WITH PASSWORD 'new-secure-crypto-password-v2!';
   GRANT arthsavora_app TO arthsavora_app_v2;
   ```
2. **Update Secrets Manager**:
   Store the new connection URI in AWS Secrets Manager as `arthsavora/prod/database_v2`.
3. **Rolling Deploy Backend Containers**:
   Deploy updated task definition referencing `database_v2`. Old and new containers operate simultaneously during rolling deployment without connection errors.
4. **Decommission Old User**:
   After 24 hours of zero connections to the previous user:
   ```sql
   REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM arthsavora_app_v1;
   DROP USER arthsavora_app_v1;
   ```

### 2.2 JWT Secret Key Rotation (`SECRET_KEY`)
1. **Generate New Key**:
   Generate a high-entropy key: `openssl rand -hex 32`.
2. **Phase 1: Dual Verification Support**:
   Configure backend to accept both the legacy key and the new key for token verification, but sign all new tokens with the new key.
3. **Phase 2: Wait for Access Token TTL**:
   Wait for maximum access token TTL (24 hours). All active user sessions refresh and receive tokens signed by the new key.
4. **Phase 3: Deprecate Legacy Key**:
   Remove legacy key from configuration. Any remaining stale tokens are rejected and require re-authentication.

### 2.3 Third-Party API Key Rotation (Gemini AI / External Providers)
1. Generate new API key in Google AI Studio / Google Cloud Console.
2. Update `GEMINI_API_KEY` in AWS Secrets Manager.
3. Trigger rolling restart of ECS backend tasks.
4. Verify AI Assistant responsiveness via `/api/v1/assistant/chat`.
5. Revoke previous API key in Google Cloud Console.

## 3. Incident Rotation Trigger (Emergency Rotation)

In the event of suspected credential exposure:
1. Immediately invoke the **Production Incident Runbook** ([PRODUCTION_INCIDENT_RUNBOOK.md](file:///d:/Arthsavora/docs/PRODUCTION_INCIDENT_RUNBOOK.md)).
2. Revoke active JWT tokens globally by bumping the global token issuance epoch or invalidating all active refresh sessions.
3. Execute immediate out-of-band secret replacement via AWS Secrets Manager.
4. Trigger rolling restart with container replacement.

## 4. Cross-Reference Links
- Secrets Configuration: [SECRETS_AND_ENVIRONMENT_CONFIGURATION.md](file:///d:/Arthsavora/docs/SECRETS_AND_ENVIRONMENT_CONFIGURATION.md)
- Production Incident Runbook: [PRODUCTION_INCIDENT_RUNBOOK.md](file:///d:/Arthsavora/docs/PRODUCTION_INCIDENT_RUNBOOK.md)
