# ARTHSAVORA — Mobile Navigation Architecture

**Document Reference:** `docs/MOBILE_NAVIGATION.md`  
**Authoritative Standard:** Stage 6 Mobile Shell & Touch Navigation  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Executive Summary

Mobile financial management requires quick access to daily actions (recording an expense, checking an account balance, snapping a receipt) while preserving full access to advanced modules (general ledger, forecasting, GST readiness, entity workspaces).

ARTHSAVORA achieves this balance through a **hybrid dual-layer navigation model**:
1. **Primary Bottom Navigation (`MobileTabBar.tsx`):** Five high-frequency actions accessible with one thumb.
2. **Comprehensive Slide-Out Drawer (`Sidebar.tsx`):** Complete categorized hierarchy covering all 19 application routes.

---

## 2. The Primary Mobile Tab Bar (`MobileTabBar.tsx`)

The bottom tab bar is pinned to the base of the mobile viewport (`fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 border-t border-slate-800 backdrop-blur-lg`):

```
┌────────────────────────────────────────────────────────┐
│  [Home]    [Accounts]    ( + )    [Scan]    [Alerts]   │
│   ( / )    (/accounts)  (Add Tx) (/documents) (/notifs) │
└────────────────────────────────────────────────────────┘
```

### Destination Breakdown:
1. **Home (`/`):** Instant return to the financial dashboard, net worth overview, and cash-flow summaries.
2. **Accounts (`/accounts`):** Full list of bank accounts, credit cards, assets, and liabilities.
3. **Add Transaction (Center Elevated Action):** An elevated circular Indigo button (`w-12 h-12 rounded-full -mt-5 bg-gradient-to-tr from-indigo-600 to-indigo-500`) linking to `/transactions?action=new` to trigger rapid expense or income entry.
4. **Scan (`/documents?action=scan`):** Opens the mobile camera capture modal for fast receipt ingestion.
5. **Alerts (`/notifications`):** Displays real-time financial alerts with a live unread counter badge.

---

## 3. The Slide-Out Drawer Navigation

When secondary or deeper workflows are needed (e.g. General Ledger postings, Monte Carlo forecasting, Tax Intelligence, or Workspace switching):
- The user taps the hamburger menu icon (`Menu`) in the top bar.
- The drawer slides smoothly from the left with an animated backdrop overlay (`bg-black/75 backdrop-blur-sm`).
- Displays the complete categorized navigation tree:
  - Core Ledger & Accounts
  - Planning & Budgets
  - Intelligence & Compliance
  - Entity Workspaces (Family, Business, Settings)
- Tapping any link or the close icon (`X`) immediately dismisses the drawer and navigates to the destination.
