# ARTHSAVORA CI/CD PIPELINE & DEPLOYMENT STANDARD
## Automated Verification, Quality Gates & Continuous Integration

---

## 1. Pipeline Architecture

Arthsavora utilizes **GitHub Actions** for continuous integration and automated quality enforcement. The workflow definition is located at `.github/workflows/ci.yml`.

```text
Pull Request / Push to main/dev
              │
      ┌───────┴───────┐
      ▼               ▼
[ backend-checks ]   [ frontend-checks ]
  - Python 3.11        - Node.js 22 + pnpm 12
  - Dependencies       - Lockfile verification
  - Pytest Suite       - tsc --noEmit (All workspaces)
                       - ESLint (--max-warnings 0)
                       - Vitest Component Tests
                       - Vite Production Build
      │               │
      └───────┬───────┘
              ▼
   [ All Checks Pass -> Ready to Merge ]
```

---

## 2. Automated Quality Gates

Every commit pushed to `main` or included in a pull request must pass both parallel jobs:

### Job 1: `backend-checks`
- **Environment:** `ubuntu-latest` with Python 3.11.
- **Dependency Installation:** `pip install -r backend/requirements.txt pytest pytest-asyncio httpx`.
- **Test Execution:** `pytest backend/tests` executing all configuration, exception, health, and security tests.

### Job 2: `frontend-checks`
- **Environment:** `ubuntu-latest` with Node.js 22 and `pnpm@12.18.0`.
- **Dependency Integrity:** `pnpm install --frozen-lockfile` (ensures `pnpm-lock.yaml` is deterministic).
- **Type Checking:** `pnpm -r run typecheck` across `@arthsavora/contracts`, `@arthsavora/design-tokens`, `@arthsavora/utilities`, `@arthsavora/validation`, and `@arthsavora/web`.
- **Code Quality:** `pnpm --filter @arthsavora/web lint` with strict zero-warning policy.
- **Unit & Component Testing:** `pnpm --filter @arthsavora/web test` executing all Vitest tests.
- **Production Compilation:** `pnpm --filter @arthsavora/web build` verifying production bundle generation.

---

## 3. Branching & Merge Governance

1. **Target Branches:**
   - `main`: Production release branch. Direct unverified pushes are strictly prohibited.
   - `dev`: Active integration branch where features and prompt completions land.
2. **Commit Standard:** All commits must follow the Conventional Commits format (`feat(...)`, `fix(...)`, `docs(...)`, `refactor(...)`).
3. **Secret Scanning Invariant:** No `.env` files, API keys, private tokens, or database credentials may ever be committed. Workflow runs are configured to immediately reject and fail on detected secret patterns.
4. **Non-Destructive Git:** Rebase and fast-forward merges are preferred; force-pushes (`git push --force`) are permanently disabled on protected branches.
