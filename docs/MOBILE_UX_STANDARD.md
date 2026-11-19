# ARTHSAVORA — Mobile UX & Touch Ergonomics Standard

**Document Reference:** `docs/MOBILE_UX_STANDARD.md`  
**Authoritative Standard:** Stage 6 Mobile User Experience & Responsive Design  
**Version:** 1.0.0  
**Last Updated:** 2026-11-19  

---

## 1. Principles of Mobile Financial Design

Financial interfaces on mobile devices demand high precision, minimal typing effort, readable numbers, and zero accidental submissions. ARTHSAVORA enforces:
1. **Touch Target Dimensions:** Minimum 44px × 44px (recommended 48px × 48px) for all primary interactive elements.
2. **Numeric Keyboards for Financial Amounts:** Inputs accept `inputMode="decimal"` and `pattern="[0-9]*"` to trigger the numeric keypad immediately on iOS and Android.
3. **One-Tap Amount Increments:** Fast tap buttons (`+₹100`, `+₹500`, `+₹1000`, `+₹5000`) for rapid cash and expense logging.
4. **Adaptive Viewports (Table vs Card):** Dense multi-column tables switch to readable touch cards on viewports under 768px.
5. **No Horizontal Page Overflow:** Viewports are bounded by `max-w-full overflow-x-hidden`. Content never forces horizontal scrolling at the document level.

---

## 2. Responsive Breakpoint Matrix

| Viewport | Device Class | Navigation Pattern | Table Rendering | Bottom Tab Bar |
| :--- | :--- | :--- | :--- | :--- |
| `< 640px` (sm) | Smartphones | Compact Header + Drawer | Responsive Cards | **Active (`MobileTabBar`)** |
| `640px – 768px` (md)| Large Phones / Phablets| Compact Header + Drawer | Responsive Cards | **Active (`MobileTabBar`)** |
| `768px – 1024px` (lg)| Tablets / Foldables | Desktop Sidebar (Collapsible)| Standard Table (Scrollable)| Inactive |
| `> 1024px` (xl) | Laptops / Workstations | Fixed Categorized Sidebar | Full Expanded Table | Inactive |

---

## 3. Touch Gestures & Mobile Dialogs

- **Bottom Sheet Behavior:** Modals on mobile devices slide up from the bottom with curved top corners (`rounded-t-2xl sm:rounded-2xl`).
- **Backdrop Dismissal:** Tapping outside the modal container or pressing the hardware/gesture back button safely closes modals without submitting state.
- **Double-Submission Prevention:** Form action buttons toggle to `isLoading={true}` and `disabled={true}` while mutations are in-flight, preventing duplicate transactions from double taps.
- **Safe Area Padding:** Content pads properly against modern device notches and gesture navigation bars using `pb-safe` / `pb-24`.
