# ARTHSAVORA — Frontend Routing Architecture

**Document Reference:** `docs/FRONTEND_ROUTING.md`  
**Authoritative Standard:** Stage 5/6 Route Manifest & Access Guarding  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview

ARTHSAVORA uses `react-router-dom` (v6) for declarative client-side routing, route guard enforcement, parameter binding, and programmatic view switching. Every financial view is mapped to a canonical route URL, allowing deep-linking, bookmarking, and deterministic browser history navigation.

---

## 2. Route Manifest & Mapping

The application defines 19 primary client routes mounted inside `apps/web/src/App.tsx`:

| Path | Primary Component | Workspace Applicability | Description |
| :--- | :--- | :--- | :--- |
| `/` | `Dashboard.tsx` | Personal, Family, Business | Primary overview, net worth, cash flow & budget status |
| `/accounts` | `Accounts.tsx` | All | Bank accounts, credit cards, assets, liabilities |
| `/transactions` | `Transactions.tsx` | All | Authoritative ledger transactions with search/filters |
| `/ledger` | `Ledger.tsx` | All | General ledger journal entries, postings, double-entry verification |
| `/import` | `Import.tsx` | All | CSV/PDF statement parsing and batch ingestion pipeline |
| `/budgets` | `Budgets.tsx` | Personal, Family | Category budgets, spending limits, rollover management |
| `/goals` | `Goals.tsx` | Personal, Family | Savings goals, milestone tracking, ledger velocity |
| `/recurring` | `Recurring.tsx` | All | Subscriptions, recurring bills, cash-flow commitments |
| `/forecast` | `Forecast.tsx` | All | Cash-flow predictions, Monte Carlo simulations, scenarios |
| `/categories` | `Categories.tsx` | All | Expense/income category taxonomy & merchant intelligence |
| `/anomalies` | `Anomalies.tsx` | All | Financial anomaly signals, fraud detection & risk audits |
| `/documents` | `Documents.tsx` | All | Receipt OCR, invoice processing, line-item extraction |
| `/assistant` | `Assistant.tsx` | All | Conversational AI financial assistant with tool execution |
| `/reports` | `FinancialReports.tsx` | All | P&L, Cash Flow, Balance Sheet, Trial Balance, Export |
| `/tax-intelligence` | `FinancialReports.tsx` | All | Tax classification, GST readiness, Section 115BAC estimator |
| `/connections` | `FinancialConnections.tsx`| All | RBI Account Aggregator consents, sync lifecycle |
| `/family` | `Family.tsx` | Family Workspaces | Collaborative household finance, allocations, member privacy |
| `/business` | `Business.tsx` | Business Workspaces | Client/vendor invoicing, AR/AP, business profitability |
| `/notifications` | `Notifications.tsx`| All | Unified notification center, alert rules, delivery history |
| `/settings` | `Settings.tsx` | All | User profile, workspace config, RBAC members, preferences |
| `/profile` | `Settings.tsx` | All | User identity and authentication settings |

---

## 3. Dynamic Breadcrumb Generation

The `TopBar` component parses `location.pathname` to generate hierarchical breadcrumbs dynamically:

```typescript
const pathSegments = location.pathname.split('/').filter(Boolean);
// Examples:
// / -> "Dashboard"
// /reports -> "Dashboard / Financial Reports"
// /settings -> "Dashboard / Settings"
```

Each segment maps to a friendly label via a route map lookup dictionary, rendering accessible navigation links that allow users to jump backward through the hierarchy.

---

## 4. Protected Route & Auth Guards

All financial routes are wrapped within `AppLayout`:
1. **Unauthenticated Redirects:** If `useAuthStore.getState().isAuthenticated` evaluates to `false`, the router directs the browser to the login/onboarding view.
2. **Entity-Aware Route Highlighting:** While all routes are accessible, workspace-specific views (e.g. `/business` or `/family`) display contextual notices if viewed while in an alternate workspace mode, offering single-click workspace switching.
3. **Route Error Fallbacks:** Unknown or malformed URLs render a clean 404 EmptyState view within the shell with a single click button to return to the `/` Dashboard.
