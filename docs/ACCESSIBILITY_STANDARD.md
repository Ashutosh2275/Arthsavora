# ARTHSAVORA ACCESSIBILITY STANDARD (WCAG 2.2 AA)
## Commercial FinTech Accessibility Compliance & Verification Protocol

---

## 1. Compliance Target & Principles

Arthsavora targets full compliance with the **Web Content Accessibility Guidelines (WCAG) 2.2 Level AA**. Financial applications handle critical personal and commercial decisions; therefore, every user—regardless of ability, neurodivergence, or assistive technology—must have complete, unambiguous access to financial statements, transaction histories, and controls.

### Fundamental Rules
1. **Perceivable:** Financial information and interface components must be presentable to users in ways they can perceive.
2. **Operable:** All interface components, navigation flows, and interactive controls must be operable via keyboard.
3. **Understandable:** Information and operation of the financial UI must be clear, predictable, and forgiving of errors.
4. **Robust:** Content must be robust enough that it can be interpreted reliably by assistive technologies, including screen readers.

---

## 2. Specific Requirements & Implementation Guidelines

### 2.1 Color Contrast Ratios (WCAG 1.4.3 & 1.4.11)
- **Normal Text (under 18pt / 24px):** Minimum contrast ratio of **4.5:1** against its background.
  - Arthsavora Dark Theme: Primary text `#f8fafc` on `#0b0f1a` delivers a **15.8:1** contrast ratio (Exceeds WCAG AAA).
  - Secondary text `#94a3b8` on `#0f172a` delivers a **5.7:1** contrast ratio (Exceeds WCAG AA).
- **Large Text (18pt+ or 14pt+ bold):** Minimum contrast ratio of **3.0:1**.
- **UI Components & Graphical Objects:** Active controls, borders, and status icons must have at least **3.0:1** contrast against adjacent colors.

### 2.2 Non-Text Contrast & Color Independence (WCAG 1.4.1)
- **The Color Independence Rule:** Color must **never** be used as the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element.
- **Financial Status Implementation:**
  - Income is green (`#10b981`), but must **always** include a `+` symbol and upward arrow or checkmark.
  - Expenses are rose (`#f43f5e`), but must **always** include a `-` symbol and downward arrow.
  - Status badges must pair color fills with distinct SVG icons and explicit textual descriptors (`Pending`, `Cleared`, `Reconciled`, `Failed`).

### 2.3 Keyboard Navigation & Focus Management (WCAG 2.1.1, 2.1.2, 2.4.7)
- Every interactive element must be reachable and actionable via keyboard alone (`Tab`, `Shift+Tab`, `Enter`, `Space`, and Arrow keys).
- **Visible Focus Rings:**
  ```css
  .focus-ring {
    @apply focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900;
  }
  ```
  Suppressing focus rings with `outline: none` without providing an equivalent focus indicator is strictly forbidden.
- **Focus Traps in Modals:** When a modal or confirmation dialog opens, keyboard focus must be directed into the dialog container and trapped inside it until dismissed. Pressing `Escape` must close the modal and return focus to the trigger button.

### 2.4 Forms & Error Identification (WCAG 3.3.1, 3.3.2)
- Form fields must have programmatic labels linked via `<label htmlFor="...">` and `<input id="...">`.
- Invalid fields must include `aria-invalid="true"`.
- Error messages must use `<p role="alert">` and be referenced via `aria-describedby` so screen readers announce the validation failure immediately.

### 2.5 Reduced Motion (WCAG 2.3.3)
- Respect system-level accessibility settings:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
- Animations must not delay user financial operations or cause disorienting layout shifts.

---

## 3. Accessibility Testing Protocol

Before merging any UI pull request:
1. **Keyboard-Only Audit:**
   - Navigate the entire view using only `Tab`, `Shift+Tab`, `Enter`, and `Space`.
   - Verify every input and button has a high-contrast focus ring.
   - Verify modals trap focus and dismiss on `Escape`.
2. **Screen Reader Verification:**
   - Verify NVDA (Windows) or VoiceOver (macOS) correctly announces button states (`aria-busy="true"` for loading buttons), form validation errors, and financial status tags.
3. **Automated Component Checks:**
   - Run Vitest component tests (`pnpm --filter @arthsavora/web test`) checking accessibility attributes (`aria-disabled`, `aria-busy`, `role="dialog"`, `role="alert"`).
