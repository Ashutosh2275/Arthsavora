# ARTHSAVORA — Deep-Link Architecture & URL Routing

**Document Reference:** `docs/DEEP_LINK_ARCHITECTURE.md`  
**Authoritative Standard:** Stage 6 Deep Linking & Native App Readiness  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview & Objectives

Deep linking allows users to navigate directly to specific financial records, active modals, and intelligence views from external sources (such as push notifications, emails, desktop shortcuts, or mobile home screens).

The ARTHSAVORA deep-link architecture guarantees:
1. **Deterministic State Restoration:** Resolving a link always restores the target route and active workspace tenant context.
2. **Safe Action Parameters:** Workflows can be triggered via safe query parameters (e.g. `?action=new`, `?action=scan`).
3. **No Sensitive Information in URLs:** Account numbers, tokens, balances, and passwords are NEVER exposed in URL path segments or query parameters.
4. **Authentication Guards:** Resolving a deep link while unauthenticated preserves the target URL in session redirect memory, returning the user to the destination immediately after login.

---

## 2. Canonical URL Schema & Action Map

| Canonical URL Path | Supported Query Actions | Resulting Application View |
| :--- | :--- | :--- |
| `/` | `?workspace_id={id}` | Loads Dashboard for the specified workspace |
| `/transactions` | `?action=new` | Opens "Record Financial Transaction" modal |
| `/transactions` | `?status=pending` | Filters ledger transactions to pending holds |
| `/documents` | `?action=scan` | Opens "Scan Receipt or Document" camera modal |
| `/documents` | `?document_id={id}` | Selects and opens side-by-side OCR review |
| `/notifications` | `?category=unread` | Opens notification center filtered to unread alerts |
| `/notifications` | `?category=security`| Displays critical security events |
| `/reports` | `?tab=gst` | Directs to GST reporting readiness tab |
| `/reports` | `?tab=tax_estimate` | Opens Section 115BAC Income Tax Estimator |
| `/connections` | `?action=new_consent`| Initiates RBI Account Aggregator consent flow |
| `/settings` | `?tab=members` | Opens workspace RBAC and member management |

---

## 3. Preparation for Native Android & iOS App Links

The current URL scheme is structured to map directly to future mobile operating system app-link registries without architectural redesign:
- **Android App Links:** Maps `https://arthsavora.internal/*` via `assetlinks.json` in `/.well-known/assetlinks.json`.
- **Apple Universal Links:** Maps `https://arthsavora.internal/*` via `apple-app-site-association` in `/.well-known/apple-app-site-association`.
- Because the frontend routing paths and backend REST APIs share identical resource naming, future native applications will consume these deep links directly.
