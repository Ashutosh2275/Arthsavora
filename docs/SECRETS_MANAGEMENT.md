# ARTHSAVORA — Secrets Management & Repository Scan Audit

## 1. Secrets Management Policy

ARTHSAVORA maintains a strict zero-credential-leakage policy. Credentials, private keys, API secrets, database passwords, and personal access tokens must **never** be committed to source control, embedded in client-side frontend code, or printed to access logs.

---

## 2. Configuration & Secrets Hierarchy

1. **Production Environment:** All sensitive configuration values are injected at container startup via environment variables supplied by a secure secrets manager (AWS Secrets Manager, Google Cloud Secret Manager, or Kubernetes Secrets).
2. **Local Development:** Developers maintain a local untracked `.env` file based on `.env.example`.
3. **Repository Files:** Only `.env.example` templates with generic placeholders (`"postgres"`, `"insecure-secret-key-change-in-production-12345678"`, `"gemini-api-key-placeholder"`) are permitted in version control.
4. **Frontend Bundles:** Vite build bundles (`apps/web/dist`) are audited to ensure zero backend database credentials or private API keys are bundled into client-side JavaScript. Only public variables prefixed with `VITE_` are accessible in frontend code.

---

## 3. Automated Repository Secrets Scan Audit

### 3.1. Scan Methodology
A comprehensive regex-based and entropy-based automated secrets scan was conducted across all **698 tracked Git files** in the repository.

Patterns scanned:
- AWS Access Key IDs (`AKIA...`, `ASIA...`)
- Private RSA / EC / DSA / OpenSSH Keys (`-----BEGIN ... PRIVATE KEY-----`)
- GitHub Personal Access Tokens (`ghp_...`, `github_pat_...`)
- Slack API Tokens (`xoxb-...`, `xoxp-...`)
- Google API Keys (`AIza...`)
- Hardcoded Secret Assignments (`secret_key = '...'`, `api_key = '...'`)
- Committed `.env` or credential files

### 3.2. Scan Execution & Findings

```
Total Git tracked files scanned: 698
Total potential secret matches: 0
Real leaked credentials: 0
Committed .env files: 0 (Only apps/web/.env.example and backend/.env.example tracked)
```

**Verdict:** The repository is **CLEAN**. Zero private credentials, production database passwords, or third-party API keys are committed in Git history.

---

## 4. Secret Exposure Incident Protocol

If a secret is ever accidentally committed or suspected of exposure:
1. **Immediate Revocation:** The exposed credential must be revoked immediately at the source provider (e.g., rotate AWS IAM key, regenerate Gemini API token, rotate database password).
2. **Do Not Re-publish:** Never attempt to "fix" a leak by committing a second file that removes the secret while leaving the secret in Git commit history.
3. **Investigation:** Inspect access logs associated with the compromised credential to assess whether unauthorized access occurred.
4. **Git History Remediation:** Use tools such as `git-filter-repo` or BFG Repo-Cleaner to purge the commit object from history, followed by forced synchronization across team members.
5. **Post-Mortem:** Document the root cause and update pre-commit hooks.
