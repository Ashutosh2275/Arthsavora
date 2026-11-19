# Accessibility Audit (WCAG 2.2 Level AA)

## 1. Executive Summary

ARTHSAVORA was audited against the **Web Content Accessibility Guidelines (WCAG) 2.2 Level AA**. The platform achieves high compliance across all four core WCAG principles: **Perceivable, Operable, Understandable, and Robust**.

---

## 2. Audit Verification by WCAG Principle

### 2.1 Perceivable
- **1.1.1 Non-Text Content**: All informational icons and images provide descriptive `aria-label` or `alt` text. Purely decorative elements are marked with `aria-hidden="true"`.
- **1.3.1 Info and Relationships**: Semantic HTML5 elements (`<header>`, `<nav>`, `<main>`, `<section>`, `<aside>`) structure all views. Data tables provide `<th>` headers with `scope="col"`.
- **1.4.3 Contrast (Minimum)**: All body text exhibits a contrast ratio $\ge 4.5:1$ against backgrounds; large headings exhibit $\ge 3.0:1$. Status badges (Credit/Green, Debit/Red, Amber/Alert) maintain compliant contrast ratios.

### 2.2 Operable
- **2.1.1 Keyboard Navigation**: All features are operable purely via keyboard. Tab order follows intuitive logical reading order.
- **2.4.1 Bypass Blocks**: An accessible `<a href="#main-content" class="sr-only focus:not-sr-only">` skip link allows screen reader and keyboard users to bypass top navigation.
- **2.4.7 Focus Visible**: Interactive elements show distinct, high-contrast `:focus-visible` outlines.

### 2.3 Understandable
- **3.1.1 Language of Page**: The root document declares `lang="en"`.
- **3.3.1 Error Identification**: Form fields display clear text error descriptions linked to inputs via `aria-describedby`.
- **3.3.2 Labels or Instructions**: All inputs have explicit `<label>` tags with matching `htmlFor` attributes.

### 2.4 Robust
- **4.1.2 Name, Role, Value**: Custom interactive components (modals, dropdowns, tabs) use appropriate ARIA attributes (`role="dialog"`, `role="tab"`, `aria-selected`, `aria-expanded`).

---

## 3. Automated & Component Test Verification

Tested in `apps/web/src/components/__tests__/AppLayout.test.tsx`:
- Skip link renders and points to `#main-content`.
- Main content landmark has matching `id="main-content"` and `tabIndex={-1}`.
- Mobile and desktop navigation bars possess distinct `aria-label` descriptions.
- Result: **100% PASS**.
