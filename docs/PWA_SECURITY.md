# ARTHSAVORA — PWA & Mobile Security Hardening

**Document Reference:** `docs/PWA_SECURITY.md`  
**Authoritative Standard:** Stage 6 Security Architecture & Mobile Threat Mitigation  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Threat Model & Mobile Security Posture

Operating a commercial financial application within a Progressive Web App (PWA) requires mitigating distinct attack vectors associated with mobile environments and browser-level caches:
- **Shared Device Data Leakage:** Other users accessing the same family tablet or public computer.
- **Cache Poisoning / Stale Accounting Records:** Tampered or outdated offline caches presenting incorrect ledger balances.
- **Lock-Screen Disclosure:** Sensitive financial figures leaking via OS notification banners.
- **Unauthorized Cross-Tenant Access:** Workspaces bleeding state into mobile memory.

---

## 2. Hardened Security Controls

### 2.1 Complete API Isolation (Network-Only)
The service worker in `sw.js` categorically ignores `/api/*` requests. No financial figures, accounts, transactions, or user records are ever stored in `CacheStorage`. When offline, the worker returns an explicit 503 JSON response.

### 2.2 Secure Session Storage
Authentication tokens are never placed in browser storage caches:
- Ephemeral in-memory state in `useAuthStore` manages runtime bearer tokens.
- Secure HttpOnly cookies manage refresh lifecycles where supported.
- `sessionStorage` or in-memory state holds transient workspace parameters.

### 2.3 Lock-Screen Redaction
Push notifications scrub all 16-digit payment card sequences and 10-character Indian PAN numbers using regular expression redaction before calling `self.registration.showNotification`.

### 2.4 Device Logout Sanitization
When a user signs out:
1. `useAuthStore` purges user profiles and session keys.
2. `useWorkspaceStore` resets active tenants.
3. In-memory data caches for accounts, transactions, and reports are reset.
4. A postMessage event `CLEAR_CACHES` instructs the service worker to purge all CacheStorage buckets.

### 2.5 Safe Area & Viewport Constraints
The application enforces `viewport-fit=cover`, `maximum-scale=5.0`, and disables unintended double-tap zooming on buttons (`touch-action: manipulation`).
