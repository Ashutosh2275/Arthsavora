# ARTHSAVORA COMPONENT GUIDELINES
## Foundational UI/UX Components Reference & API Specification

---

## 1. Component Architecture & Principles

All foundational UI components in Arthsavora reside in `apps/web/src/components/ui/`, `components/layout/`, and `components/feedback/`. They adhere to strict accessibility, modularity, and TypeScript standards:

- **Strict Typing:** All components export explicit prop interfaces extending native HTML attributes where appropriate.
- **Ref Forwarding:** Interactive components use `React.forwardRef` to allow uncontrolled form integration (e.g. React Hook Form).
- **Tailwind Utility Merging:** Class names are merged through `cn()` (`clsx` + `tailwind-merge`) ensuring zero specificity conflicts.
- **Accessible By Default:** All interactive elements feature visible focus rings, ARIA roles, and keyboard navigation.

---

## 2. Core Interactive Components

### 2.1 Button (`components/ui/button.tsx`)

A commercial fintech button supporting primary actions, destructive confirmations, secondary navigation, and icon buttons.

#### Props
```typescript
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  loadingText?: string;
}
```

#### Usage Example
```tsx
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

<Button
  variant="primary"
  size="md"
  isLoading={isSaving}
  loadingText="Recording Entry..."
  onClick={handleSave}
>
  <Plus size={16} />
  <span>Add Transaction</span>
</Button>
```

#### States Handled
- Default, Hover, Active, Focus Ring (`focus-visible:ring-indigo-500`).
- Disabled (`disabled:opacity-50 disabled:pointer-events-none`).
- Loading (`aria-busy="true"`, animated spinner with custom loading text).

---

### 2.2 Input (`components/ui/input.tsx`)

Form input with integrated labels, helper text, validation error alerts, and specialized variants.

#### Props
```typescript
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isPasswordToggle?: boolean;
  onClear?: () => void;
}
```

#### Features
- **Accessible ID Association:** Generates unique IDs linking `<label htmlFor="...">` and `<p role="alert">` via `aria-describedby`.
- **Password Visibility:** Toggleable eye icon with screen reader announcers.
- **Search Support:** Built-in search icon and clear (`X`) button.

---

### 2.3 Form Controls

- **Textarea (`components/ui/textarea.tsx`):** Multiline field with error handling and helper text.
- **Select (`components/ui/select.tsx`):** Native select wrapper styled with chevron icon and option groups.
- **Checkbox (`components/ui/checkbox.tsx`):** Accessible checkbox with SVG checkmark and focus indicator.
- **RadioGroup (`components/ui/radio.tsx`):** Styled list of selectable radio items with keyboard arrows.
- **Switch (`components/ui/switch.tsx`):** Accessible toggle switch (`role="switch"`, `aria-checked`).

---

## 3. Financial Data Presentation Components

### 3.1 FinancialAmount (`components/ui/financial-amount.tsx`)

The standard component for all currency display across Arthsavora. Formats Indian Rupees according to the Indian numbering system.

#### Props
```typescript
interface FinancialAmountProps {
  amount: number; // in Rupees
  currency?: string; // Default: 'INR'
  type?: 'income' | 'expense' | 'neutral' | 'auto';
  showSign?: boolean;
  isPrivate?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  className?: string;
}
```

#### Key Invariants
- Uses `tabular-nums font-mono` to ensure numeric columns align perfectly.
- Positive amounts render with emerald green styling; negative amounts render with rose red styling.
- `isPrivate={true}` renders masked bullets (`••••••`) when privacy mode is enabled.

---

### 3.2 PercentageDisplay (`components/ui/percentage-display.tsx`)

Displays percentage change with trend arrows (Upward / Downward / Neutral).

#### Props
```typescript
interface PercentageDisplayProps {
  value: number; // e.g., 5.4 for +5.4%
  showArrow?: boolean;
  invertColors?: boolean; // When an increase in expense is considered negative
  size?: 'xs' | 'sm' | 'md' | 'lg';
}
```

---

### 3.3 StatusBadge (`components/ui/status-badge.tsx`)

Displays transaction or account status without relying on color alone.

#### Supported Statuses
- **Transactions:** `pending`, `cleared`, `reconciled`, `failed`, `cancelled`
- **Accounts:** `active`, `frozen`, `closed`

#### AI Prediction Tag
When `isAiPredicted={true}`, renders a distinct `Sparkles` icon with the model confidence percentage (e.g. `AI (94%)`).

---

## 4. Layout & Structural Primitives

### 4.1 PageContainer (`components/layout/PageContainer.tsx`)
Max-width wrapper (`default: 1280px`, `narrow: 896px`, `wide: 1440px`) with responsive padding across mobile, tablet, and desktop viewports.

### 4.2 SectionHeader (`components/layout/SectionHeader.tsx`)
Header bar containing the page title, subtitle, optional status badge, and an actions slot for primary CTA buttons.

### 4.3 Card (`components/ui/card.tsx`)
Modular card primitive consisting of:
- `Card`: Container with `default`, `elevated`, `subtle`, and `interactive` variants.
- `CardHeader`: Title and description wrapper.
- `CardTitle`: Semibold heading.
- `CardDescription`: Subtitle copy.
- `CardContent`: Main card body.
- `CardFooter`: Bordered footer with action buttons.

---

## 5. Feedback & Dialog Components

### 5.1 Modal (`components/ui/modal.tsx`)
Accessible dialog foundation with:
- Backdrop with blur effect.
- Automatic Escape key dismissal.
- Focus trap and scroll lock on `document.body`.
- `role="dialog"` and `aria-modal="true"`.

### 5.2 ConfirmDialog (`components/ui/confirm-dialog.tsx`)
Standard confirmation dialog for destructive financial operations (deleting transactions, closing accounts, removing categories). Includes destructive alert styling and loading states.

### 5.3 Alert (`components/ui/alert.tsx`)
Feedback banner supporting `info`, `success`, `warning`, and `error` variants with dedicated icons and optional dismissal.

### 5.4 EmptyState (`components/feedback/EmptyState.tsx`)
Zero-data placeholder providing an icon, explanatory copy, and a primary action button to guide the user.

### 5.5 ErrorBoundary (`components/feedback/ErrorBoundary.tsx`)
React error boundary that catches rendering exceptions, reports them to `apps/web/src/lib/observability.ts`, displays an error reference ID, and provides an application reload button.
