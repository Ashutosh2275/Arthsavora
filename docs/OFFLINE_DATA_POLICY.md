# ARTHSAVORA — Offline Data & Local Storage Policy

**Document Reference:** `docs/OFFLINE_DATA_POLICY.md`  
**Authoritative Standard:** Stage 6 Data Governance & Device Storage Classification  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Executive Policy Statement

In commercial financial platforms, browser storage cannot be assumed confidential. ARTHSAVORA establishes a strict taxonomy governing what data may be persisted client-side and what data is prohibited from local persistence.

---

## 2. Seven-Tier Data Classification Matrix

| Tier | Category | Allowed Storage Mechanism | Encryption Required? | Cache Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Public Static Assets (CSS, JS, Web Fonts, Icons) | Service Worker `CacheStorage` | No | Pre-cached, Stale-While-Revalidate |
| **Tier 2** | Non-sensitive Application Config (Locale, Currency) | `localStorage` | No | Persisted across sessions |
| **Tier 3** | UI & Session State (Sidebar open, Active tab) | In-Memory (React State / Zustand) | N/A | Ephemeral (cleared on refresh) |
| **Tier 4** | User Preferences (Theme, Quiet hours, Channels) | `localStorage` & Server Database | No | Synced with backend preferences |
| **Tier 5** | Authoritative Financial Data (Ledger, Accounts, Txs)| In-Memory Only (`useAccountStore`, etc.) | **YES (Prohibited on Disk)** | Cleared on workspace switch / logout |
| **Tier 6** | Authentication Secrets (Access tokens, API keys) | In-Memory (`useAuthStore`) / HttpOnly Cookies | **YES (Never in CacheStorage)**| Wiped completely on logout |
| **Tier 7** | Sensitive Documents & Financial Identifiers (PAN, Aadhaar) | Server-side S3/PostgreSQL only | **YES** | **STRICTLY PROHIBITED IN LOCAL STORAGE** |

---

## 3. Storage Prohibitions & Anti-Patterns

1. **PROHIBITED: Caching API responses in Service Worker CacheStorage.**
   - All `/api/*` endpoints are explicitly excluded from `sw.js` caches.
2. **PROHIBITED: Persisting Banking Credentials or UPI PINs.**
   - ARTHSAVORA never stores, processes, or caches bank passwords, PINs, or raw CVVs.
3. **PROHIBITED: Silent Offline Queuing of Financial Transactions.**
   - If a user attempts to record a transaction while offline, the application does not queue it into `localStorage` and report it as "Saved".
   - The UI surfaces an honest notification: *"You are offline. Transactions require server verification to prevent duplicate postings."*
4. **PROHIBITED: Local Storage of Auth Tokens in Shared Caches.**
   - Tokens are kept in memory or HttpOnly cookies. No authorization headers are recorded in service worker storage.

---

## 4. Honest Offline State Indicators

The application communicates financial state with five distinct statuses:
- **Online & Synchronized:** Green status dot in header; full read/write capabilities.
- **Offline (Read-Only):** Amber banner across shell; cached interface visible, mutations disabled.
- **Pending Local Form Draft:** User has typed into a form while disconnected; draft remains in component state until submission.
- **Waiting for Network:** Form submit button disabled with *"Awaiting Connection"*.
- **Failed Synchronization:** Immediate, clear error banner with retry options.

---

## 5. Logout & Device Sanitization Protocol

Upon triggering `logout()`:
1. `useAuthStore.getState().logout()` clears in-memory tokens and user records.
2. `useWorkspaceStore.getState().reset()` evicts tenant identifiers.
3. Registered store listeners wipe all financial state trees (accounts, transactions, ledger, reports, invoices).
4. `usePwaStore.getState().clearCaches()` signals the service worker to delete all CacheStorage instances.
5. All local sessions are terminated cleanly without data remnants.
