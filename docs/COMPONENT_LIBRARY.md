# ARTHSAVORA — Frontend Component Library & UI Guidelines

**Document Reference:** `docs/COMPONENT_LIBRARY.md`  
**Authoritative Standard:** Stage 5/6 Design System & Component Engineering  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Component Philosophy & System Architecture

ARTHSAVORA components are built following the **atomic design methodology** and strictly enforce:
1. **Accessibility by Default:** Built with WAI-ARIA roles, labels, and keyboard navigability.
2. **Deterministic Layout:** Clean spacing using an 8pt grid (`space-y-4`, `p-6`, `gap-3`).
3. **Responsive Adaptability:** Mobile-first layout classes (`flex-col md:flex-row`).
4. **Theme Resilience:** Every component specifies paired light and dark Tailwind utility classes (e.g. `bg-white dark:bg-slate-900 text-slate-900 dark:text-white`).

---

## 2. Core UI Components (`apps/web/src/components/ui/`)

### 2.1 `Button.tsx`
- **Variants:** `primary` (indigo solid), `secondary` (slate outline), `outline` (border only), `danger` (rose/red), `ghost` (transparent hover).
- **Sizes:** `sm` (compact table action), `md` (standard form trigger), `lg` (onboarding call to action).
- **States:** Handles `disabled` and `isLoading` with an accessible spinning SVG loader.

### 2.2 `Input.tsx` & `Select.tsx`
- High-contrast border definitions (`border-slate-300 dark:border-slate-700`).
- Integrated label, helper text, and validation error messages.
- Accessible error bindings via `aria-invalid` and `aria-describedby`.

### 2.3 `Modal.tsx`
- Traps keyboard focus within the dialog when open.
- Closes via `Escape` key and backdrop clicks.
- Enforces `role="dialog"`, `aria-modal="true"`, and accessible naming via `aria-labelledby` or `aria-label`.

### 2.4 `Card.tsx`
- Standard surface container with elevation shadow and subtle dark borders.
- Sub-components: `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`.

### 2.5 `StatusBadge.tsx`
- Color-coded contextual badges for financial states:
  - `success` / `active` / `cleared` / `paid` (Emerald/Green).
  - `warning` / `pending` / `due` (Amber/Yellow).
  - `danger` / `failed` / `overdue` / `anomalous` (Rose/Red).
  - `neutral` / `draft` / `archived` (Slate/Gray).

### 2.6 `EmptyState.tsx`
- Provides reassuring, actionable placeholders when lists or tables are empty.
- Displays an illustrative icon, title, description, and primary call-to-action button.

### 2.7 `FinancialAmount.tsx`
- Specialized financial value renderer.
- Accepts raw integer `amountPaise` (or rupee amount).
- Formats figures cleanly into the Indian numbering format (`₹1,25,000.00`).
- Applies green/red coloring based on credit/debit sign or account balance type.

### 2.8 `ThemeToggle.tsx`
- Segmented 3-state control allowing quick switching between Light (`Sun`), Dark (`Moon`), and System (`Monitor`) themes.

---

## 3. Layout & Shell Components (`apps/web/src/components/layout/`)

- **`AppLayout.tsx`:** Primary view container, skip link, mobile drawer coordinator.
- **`Sidebar.tsx`:** Desktop categorized navigation menu.
- **`TopBar.tsx`:** Sticky application header with breadcrumbs, widgets, and profile avatar.
- **`WorkspaceSwitcher.tsx`:** Multi-entity switcher and new workspace generator.
- **`GlobalSearch.tsx`:** Fast Spotlight/Command palette (`Ctrl+K`) searching across pages, accounts, transactions, and documents.
- **`OnboardingModal.tsx`:** 4-step wizard guiding first-time users through initial account setup.
