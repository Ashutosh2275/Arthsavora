# ARTHSAVORA DESIGN SYSTEM SPECIFICATION
## Institutional Commercial FinTech Visual Identity & Component Tokens

---

## 1. Executive Summary & Design Philosophy

ARTHSAVORA is an AI-powered financial management ecosystem engineered for commercial use in India. The design system rejects generic dashboard aesthetics, unnecessary decoration, and toy-like styling in favor of an **institutional, minimal, clear, and confident** commercial fintech interface.

### Core Visual Principles
1. **Financial Clarity First:** Every visual element must enhance data legibility and scanning efficiency. Decorative distractions that slow down financial decision-making are prohibited.
2. **Institutional Restraint:** Dark theme is the default institutional aesthetic (`#0b0f1a`), paired with a pristine, high-contrast light theme (`#f8fafc`). Both themes strictly conform to WCAG 2.2 AA accessibility standards.
3. **Semantic Integrity:** Financial statuses (Income, Expense, Warning, Transfer/Info) maintain strict, uncompromised meanings across all screens.
4. **Color Independence:** Color is **never** the sole medium for conveying financial or transaction states. Icons and accessible textual labels are mandatory companions.
5. **Tabular Precision:** All monetary figures, percentages, balances, and numerical tables enforce monospaced tabular numerals (`tabular-nums` / `tnum`) to ensure perfect vertical alignment across financial statements.

---

## 2. Design Tokens Architecture

Design tokens are centralized in the `@arthsavora/design-tokens` package (`packages/design-tokens/src/index.ts`) and projected into `apps/web/tailwind.config.js` and `apps/web/src/index.css` via CSS custom properties.

### 2.1 Color Palette

#### Neutral Surface Hierarchy (Dark Theme Default)
| Token Name | Value | Purpose |
|:---|:---|:---|
| `--bg-base` | `#0b0f1a` (RGB: 11 15 26) | Application root canvas background |
| `--bg-surface` | `#0f172a` (RGB: 15 23 42) | Primary card and panel surface |
| `--bg-surface-subtle` | `#1e293b` (RGB: 30 41 59) | Sub-sections, table row hover, active states |
| `--bg-elevated` | `#1e293b` (RGB: 30 41 59) | Modals, popovers, dropdowns |
| `--bg-input` | `#020617` (RGB: 2 6 23) | Text inputs, select controls, textareas |

#### Neutral Surface Hierarchy (Light Theme)
| Token Name | Value | Purpose |
|:---|:---|:---|
| `--bg-base` | `#f8fafc` (RGB: 248 250 252) | Light application canvas |
| `--bg-surface` | `#ffffff` (RGB: 255 255 255) | Card and container surface |
| `--bg-surface-subtle` | `#f1f5f9` (RGB: 241 245 249) | Subtle section dividers and hover states |
| `--bg-elevated` | `#ffffff` (RGB: 255 255 255) | Floating dialogs and menus |
| `--bg-input` | `#ffffff` (RGB: 255 255 255) | Form controls |

#### Typography & Content Hierarchy
| Token Name | Dark Theme Value | Light Theme Value | Contrast Ratio |
|:---|:---|:---|:---|
| `--text-primary` | `#f8fafc` (Slate 50) | `#0f172a` (Slate 900) | > 14:1 (WCAG AAA) |
| `--text-secondary` | `#94a3b8` (Slate 400) | `#475569` (Slate 600) | > 5.5:1 (WCAG AA) |
| `--text-muted` | `#64748b` (Slate 500) | `#64748b` (Slate 500) | > 4.5:1 (WCAG AA) |
| `--text-inverse` | `#0b0f1a` (Slate 950) | `#ffffff` (White) | > 15:1 (WCAG AAA) |

#### Brand Accent Palette
- **Primary Brand:** Indigo 600 (`#4f46e5`, RGB: `79 70 229`)
- **Primary Hover:** Indigo 500 (`#4338ca`, RGB: `67 56 202`)
- **Accent Highlight:** Indigo 500 / Violet 500 (`#6366f1`, RGB: `99 102 241`)
- **Subtle Fill:** `rgba(79, 70, 229, 0.1)`

#### Semantic Financial Status Colors
| Financial State | Dark Theme Color | Light Theme Color | Meaning & Usage |
|:---|:---|:---|:---|
| **Income / Credit / Success** | `#10b981` (Emerald 500) | `#059669` (Emerald 600) | Positive cash flow, completed payments, confirmed reconciliations |
| **Expense / Debit / Destructive** | `#f43f5e` (Rose 500) | `#e11d48` (Rose 600) | Cash outflows, failed transactions, overdraft alerts, destructive actions |
| **Warning / Pending Review** | `#f59e0b` (Amber 500) | `#d97706` (Amber 600) | Pending clearance, budget limit threshold (>85%), tax deadlines |
| **Info / Transfer** | `#38bdf8` (Sky 400) | `#0284c7` (Sky 600) | Internal account transfers, system notices, informational telemetry |
| **Neutral / Inactive** | `#94a3b8` (Slate 400) | `#64748b` (Slate 500) | Cancelled entries, archived categories, disabled states |

---

### 2.2 Typography Scale

The font system uses **Inter** for clean UI legibility and **JetBrains Mono** for all numerical and monetary data.

| Level | Size | Line Height | Font Weight | Usage |
|:---|:---|:---|:---|:---|
| `4xl` | 2.25rem (36px) | 2.5rem (40px) | Bold (700) | Hero metrics, net worth headline |
| `3xl` | 1.875rem (30px) | 2.25rem (36px) | Bold (700) | Primary dashboard balances |
| `2xl` | 1.5rem (24px) | 2.0rem (32px) | Semibold (600) | Page titles (`SectionHeader`) |
| `xl` | 1.25rem (20px) | 1.75rem (28px) | Semibold (600) | Card headings, major section titles |
| `lg` | 1.125rem (18px) | 1.75rem (28px) | Medium (500) | Modal titles, sub-card headers |
| `base` | 1.0rem (16px) | 1.5rem (24px) | Regular (400) | Standard body copy, form inputs |
| `sm` | 0.875rem (14px) | 1.25rem (20px) | Regular (400) | Table data cells, secondary notes |
| `xs` | 0.75rem (12px) | 1.0rem (16px) | Medium / Semibold | Field labels, status badges, captions |

#### Tabular Number Rules
```css
.tabular-nums {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "cv05" 1;
}
```
All instances of `FinancialAmount` and `PercentageDisplay` automatically inject `tabular-nums font-mono`.

---

### 2.3 Spacing Scale (4px Base Grid)

| Token | Dimension | Use Case |
|:---|:---|:---|
| `0.5` | 2px | Micro borders, fine indicators |
| `1` | 4px | Tight badge padding, icon gap |
| `2` | 8px | Button small padding, input vertical gap |
| `3` | 12px | Form control spacing, badge horizontal padding |
| `4` | 16px | Input field horizontal padding, small card padding |
| `5` | 20px | Standard card inner spacing |
| `6` | 24px | Card padding, stack spacing |
| `8` | 32px | Section vertical spacing, page headers |
| `12` | 48px | Major dashboard section dividers |
| `16` | 64px | Page bottom padding, hero spacing |

---

### 2.4 Radii & Shape

- `none`: 0px
- `sm`: 6px (Badges, small tags, tooltips)
- `md`: 8px (Buttons, form inputs, dropdown options)
- `lg`: 12px (Cards, section containers, alerts)
- `xl`: 16px (Modals, primary metric cards)
- `2xl`: 24px (Hero containers, large panels)
- `full`: 9999px (Pills, user avatars, toggle switches)

---

### 2.5 Shadows & Elevation

Depth is restrained and functional, avoiding muddy glassmorphism.
- `subtle`: `0 1px 2px 0 rgba(0, 0, 0, 0.05)` (Form controls, small buttons)
- `card`: `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)` (Standard cards)
- `dropdown`: `0 10px 15px -3px rgba(0, 0, 0, 0.25)` (Select menus, action menus)
- `modal`: `0 25px 50px -12px rgba(0, 0, 0, 0.45)` (Dialogs, confirm boxes)

---

### 2.6 Responsive Breakpoints

| Breakpoint | Minimum Width | Target Devices | Layout Behavior |
|:---|:---|:---|:---|
| `sm` | 640px | Large phones, small tablets | 2-column metric cards, stack forms |
| `md` | 768px | Tablets, iPad | Desktop top navigation reveals, sidebar expand |
| `lg` | 1024px | Small laptops, desktop | 3-column metric grids, full table rows |
| `xl` | 1280px | Standard desktop monitors | Max content width constrained to 1280px |
| `2xl` | 1536px | Ultra-wide displays | Centered container with balanced margins |

---

### 2.7 Motion Standards

- Transitions exist solely to provide interaction feedback (hover, focus, modal entry).
- **Durations:**
  - Fast: `150ms` (Buttons, checkboxes, toggles)
  - Normal: `200ms` (Dropdowns, alerts, tab switches)
  - Slow: `300ms` (Modals, drawer navigation)
- **Reduced Motion Support:**
  When `prefers-reduced-motion: reduce` is detected in system settings, animation and transition durations are clamped to `0.01ms`.

---

## 3. Mandatory Financial Product Design Invariants

Every financial screen and component in Arthsavora must strictly enforce these rules:

1. **Indian Currency Representation:** All amounts use `formatINR` with the `₹` symbol, proper lakh/crore commas (`1,50,000.00`), and 2 decimal places for paise.
2. **Tabular Numerals:** Always apply `.tabular-nums` and monospace font to numeric values.
3. **Credit vs. Debit Distinctions:** Credits/Income must display `+₹` with Emerald green styling; debits/Expenses must display `-₹` with Rose red styling.
4. **Color Independence:** Status badges must always include an icon and descriptive text (e.g. Clock icon for Pending, CheckCircle for Cleared).
5. **AI Prediction Transparency:** Any value or category predicted by AI/ML must be decorated with an AI badge (`Sparkles` icon and confidence score percentage).
6. **Privacy Mode:** Financial figures must support obfuscation (`••••••`) when privacy toggle is engaged.
7. **Destructive Action Confirmation:** Deleting transactions, clearing ledgers, or closing accounts must require a double confirmation modal (`ConfirmDialog`).
8. **No Fake/Placeholder Data:** Empty states must provide actionable next steps rather than mock data.
