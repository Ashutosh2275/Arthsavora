# ARTHSAVORA — Frontend Accessibility Specification (WCAG 2.2 AA)

**Document Reference:** `docs/FRONTEND_ACCESSIBILITY.md`  
**Authoritative Standard:** Stage 5/6 Accessibility & Inclusive Design  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Compliance Standard & Philosophy

ARTHSAVORA is engineered to comply with **WCAG 2.2 Level AA** standards. Because financial interfaces involve high-stakes decision-making, visual clarity, predictable keyboard interaction, and assistive technology support are foundational requirements rather than optional enhancements.

---

## 2. Key Accessibility Implementations

### 2.1 Skip to Main Content Link
- Embedded at the very beginning of the DOM tree in `AppLayout.tsx`:
  ```tsx
  <a
    href="#main-content"
    className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 z-50 px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white"
  >
    Skip to main content
  </a>
  ```
- Allows screen reader and keyboard-only users to bypass repetitive navigation links on every page load.

### 2.2 Landmark & Semantic HTML
- `<header role="banner">` wraps the application's top navigation bar.
- `<nav aria-label="Main Navigation">` wraps the desktop sidebar and mobile navigation drawer.
- `<main id="main-content" role="main">` houses the primary page content.
- `<aside>` wraps contextual side panels and secondary intelligence widgets.
- Headings follow a strict hierarchical structure (`<h1>` per page, followed by logical `<h2>` and `<h3>` section titles).

### 2.3 Focus Visibility & Keyboard Flow
- `focus-visible` outline styles are explicitly configured across all interactive elements (`button`, `a`, `input`, `select`).
- High-contrast indigo focus rings (`focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2`) ensure focus states remain prominently visible against both light and dark backgrounds.
- Tab index ordering follows visual reading order (`tabIndex={0}` or native focusable elements). Disabling elements uses `disabled` attributes rather than `tabIndex="-1"`.

### 2.4 Modal Dialog Focus Trapping & Accessible Names
- Every modal container specifies:
  - `role="dialog"`
  - `aria-modal="true"`
  - Explicit accessible name via `aria-label` or `aria-labelledby`.
- Modals support closing via the standard `Escape` key.
- When a modal opens, initial focus is directed to the first input or primary action.

### 2.5 Contrast Ratios & Dark Mode Verification
- All text elements meet or exceed the minimum 4.5:1 contrast ratio for normal text and 3:1 for large text.
- Dark mode utilizes deep slate backgrounds (`bg-slate-900`, `bg-slate-950`) paired with bright slate text (`text-slate-100`, `text-slate-200`) and high-contrast accent colors.
- Financial credit/debit indicators avoid relying exclusively on color by including explicit signs (`+` / `-`) or badge labels (`Credit` / `Debit`).
