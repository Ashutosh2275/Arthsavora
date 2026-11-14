# Arthsavora — Financial Goals & Milestone Tracking Engine

## 1. Overview & Objective

Financial goals allow users to establish target-based savings milestones, reserve capital for key life events, and monitor savings pacing over time.

In Arthsavora, financial goals maintain clear accounting boundaries:
- **Earmarked Reserves**: Contributing to a financial goal is an internal capital allocation/hold. It does **not** create artificial income or expense records.
- **Liquidity Traceability**: Goal balances reflect real accumulated savings held across verified accounts.
- **Deterministic Pacing**: Pacing evaluates whether the user's current accumulated balance and remaining time are sufficient to achieve the milestone without relying on unrealistic assumptions.

---

## 2. Goal Types & Classifications

Arthsavora supports 8 core goal types:

| Goal Type | Default Icon | Color Accent | Description |
|---|---|---|---|
| `emergency_fund` | `shield` | Emerald (`#10b981`) | 3 to 6 months of liquid living expenses. |
| `personal_savings` | `target` | Indigo (`#6366f1`) | General wealth accumulation. |
| `travel` | `compass` | Sky (`#0ea5e9`) | Vacation and holiday reserves. |
| `vehicle` | `car` | Amber (`#f59e0b`) | Down payment or vehicle purchase. |
| `home` | `home` | Purple (`#8b5cf6`) | Real estate or home renovation fund. |
| `education` | `book-open` | Blue (`#3b82f6`) | Tuition, courses, or children's education. |
| `debt_repayment` | `trending-down` | Rose (`#f43f5e`) | Sinking fund to retire personal debts or credit card loans. |
| `custom` | `sparkles` | Slate (`#64748b`) | Bespoke milestone defined by user. |

---

## 3. Pacing & Required Monthly Savings Formulation

Given:
- $T_{\text{paise}}$: Target amount in paise ($T_{\text{paise}} > 0$).
- $C_{\text{paise}}$: Current accumulated amount in paise ($C_{\text{paise}} \ge 0$).
- $D_{\text{start}}$: Goal start date.
- $D_{\text{target}}$: Optional target completion date.
- $D_{\text{today}}$: As of evaluation date.

### 3.1 Completion Percentage ($P$)
$$P = \min\left(100.00, \text{round}\left(\frac{C_{\text{paise}}}{T_{\text{paise}}} \times 100, 2\right)\right)$$

### 3.2 Remaining Amount to Fund ($R_{\text{paise}}$)
$$R_{\text{paise}} = \max(0, T_{\text{paise}} - C_{\text{paise}})$$

### 3.3 Required Monthly Savings Rate ($M_{\text{req}}$)
When a target date $D_{\text{target}}$ is specified and $D_{\text{target}} > D_{\text{today}}$:
$$D_{\text{rem}} = D_{\text{target}} - D_{\text{today}}$$
$$\text{Months Remaining} = \max\left(0.5, \frac{D_{\text{rem}}}{30.4375}\right)$$
$$M_{\text{req}} = \left\lceil \frac{R_{\text{paise}}}{\text{Months Remaining}} \right\rceil \quad (\text{paise per month})$$

If $R_{\text{paise}} = 0$ (target reached), $M_{\text{req}} = 0$.

---

## 4. Status Transition State Machine

```
              ┌──────────────┐
              │    ACTIVE    │
              └───┬───────▲──┘
                  │       │
  Balance >= Target       Balance < Target (Withdrawal)
                  │       │
              ┌───▼───────┴──┐
              │  COMPLETED   │
              └──────────────┘
```

1. **Auto-Completion**: When a contribution causes $C_{\text{paise}} \ge T_{\text{paise}}$, the goal automatically transitions from `active` to `completed`.
2. **Auto-Reversion**: If a subsequent withdrawal reduces $C_{\text{paise}} < T_{\text{paise}}$, the goal automatically reverts from `completed` back to `active`.
3. **Manual Controls**: Users can explicitly set the goal status to `paused` or `archived`.

---

## 5. File References

- Goal Domain Engine: [budget.py](file:///d:/Arthsavora/backend/app/domain/budget.py)
- Service Layer: [goal_service.py](file:///d:/Arthsavora/backend/app/services/budget/goal_service.py)
- Frontend UI: [Goals.tsx](file:///d:/Arthsavora/apps/web/src/pages/Goals.tsx)
- Zustand Store: [useGoalStore.ts](file:///d:/Arthsavora/apps/web/src/store/useGoalStore.ts)
