# ARTHSAVORA — Application Shell & Navigation System

**Document Reference:** `docs/APPLICATION_SHELL.md`  
**Authoritative Standard:** Stage 5/6 Frontend Navigation  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Overview & Architectural Goals

The ARTHSAVORA Application Shell (`AppLayout.tsx`) serves as the primary visual and structural container for the entire web experience. Prior to Prompt 25, navigation was crowded into a horizontal header containing 19 top-level links, causing severe visual clutter and poor ergonomics on small screens.

The Unified Application Shell delivers:
1. **Collapsible, Categorized Desktop Sidebar:** Organizes 16+ core routes into four distinct cognitive groups.
2. **TopBar Command Center:** Contextual breadcrumbs, Global Search trigger (`Ctrl+K`), Workspace Switcher, AI Assistant Launcher, Notification Center bell with live badge, Theme Toggle, and User Profile menu.
3. **Responsive Mobile Drawer:** Smooth slide-out mobile drawer with touch-friendly navigation targets.
4. **Accessibility First (WCAG 2.2 AA):** Dedicated "Skip to main content" link, proper landmark semantics (`<header>`, `<nav>`, `<aside>`, `<main>`), and complete keyboard focus-visible styling.

---

## 2. Shell Anatomy

```
┌────────────────────────────────────────────────────────────────────────┐
│ TopBar: [Logo/Menu] Breadcrumbs | [Ctrl+K Search] [Workspace] [Theme] [Profile] │
├───────────────────┬────────────────────────────────────────────────────┤
│ Sidebar:          │ Main View Area (<main id="main-content">)          │
│                   │                                                    │
│ ── CORE LEDGER ── │   ┌──────────────────────────────────────────────┐ │
│ • Dashboard       │   │ Page Header (Title, Subtitle, Actions)       │ │
│ • Accounts        │   ├──────────────────────────────────────────────┤ │
│ • Transactions    │   │                                              │ │
│ • General Ledger  │   │ Page Content (Cards, Tables, Visualizations) │ │
│ • Statement Import│   │                                              │ │
│                   │   │                                              │ │
│ ── PLANNING ──    │   │                                              │ │
│ • Budgets         │   │                                              │ │
│ • Financial Goals │   │                                              │ │
│ • Recurring Subs  │   │                                              │ │
│ • Forecasting     │   │                                              │ │
│                   │   │                                              │ │
│ ── INTELLIGENCE ──│   │                                              │ │
│ • Categories      │   │                                              │ │
│ • Anomaly Defense │   │                                              │ │
│ • Document OCR    │   │                                              │ │
│ • AI Assistant    │   │                                              │ │
│ • Reports & Tax   │   │                                              │ │
│ • Aggregators     │   │                                              │ │
│                   │   │                                              │ │
│ ── WORKSPACES ──  │   │                                              │ │
│ • Family Finance  │   │                                              │ │
│ • Business Ops    │   │                                              │ │
│ • Settings        │   │                                              │ │
└───────────────────┴────────────────────────────────────────────────────┘
```

---

## 3. Core Shell Components

### 3.1 `AppLayout.tsx`
- Encapsulates the overall layout grid (`min-h-screen flex flex-col md:flex-row`).
- Mounts the `Skip to main content` anchor tag pointing to `#main-content`.
- Coordinates mobile sidebar drawer open/close states.
- Mounts global overlays: `OnboardingModal` and `GlobalSearch`.

### 3.2 `Sidebar.tsx`
- Fixed width on desktop (`w-64`), hidden on mobile viewports.
- Grouped navigation links with Lucide icons:
  - **Core Ledger & Accounts:** Dashboard (`/`), Accounts (`/accounts`), Transactions (`/transactions`), General Ledger (`/ledger`), Statement Import (`/import`).
  - **Planning & Budgets:** Budgets (`/budgets`), Goals (`/goals`), Recurring & Subscriptions (`/recurring`), Forecast & Scenarios (`/forecast`).
  - **Intelligence & Compliance:** Categories (`/categories`), Anomaly Defense (`/anomalies`), Document OCR (`/documents`), AI Assistant (`/assistant`), Reports & Tax (`/reports`), Bank Aggregators (`/connections`).
  - **Entity Workspaces:** Family Finance (`/family`), Business Operations (`/business`), Platform Settings (`/settings`).
- Features a bottom system block displaying active workspace pill and settings shortcut.

### 3.3 `TopBar.tsx`
- Sticky header (`sticky top-0 z-30`).
- Displays breadcrumb navigation automatically computed from the active route location.
- Hosts key interactive widgets:
  - Search trigger with `Ctrl+K` visual keyboard shortcut indicator.
  - Workspace selector dropdown showing active entity (Personal, Family, Business).
  - Quick-action buttons: AI Assistant launcher (`/assistant`) and Notification bell (`/notifications`) with real-time unread counter badge.
  - Theme segmented toggle (Light, Dark, System).
  - User initials profile avatar and dropdown menu with shortcuts to Profile, Security Settings, and Sign Out.

---

## 4. Accessibility & Keyboard Navigation Specifications

1. **Skip to Main Content:** First focusable element on any page load. Visually hidden by default using `sr-only`, becomes visible at top-left (`focus:not-sr-only focus:fixed focus:top-4 focus:left-4 z-50`) upon pressing `Tab`.
2. **Keyboard Focus Rings:** All interactive buttons and navigation links use high-contrast focus rings: `focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900`.
3. **Screen Reader Landmarks:** Distinct `<nav aria-label="Main Navigation">`, `<header role="banner">`, and `<main id="main-content" role="main">` tags ensure screen reader users can quickly jump between sections.
