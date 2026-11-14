# Arthsavora — Recurring Pattern Detection & Intelligence

## 1. Scope & Objective

Users frequently have regular bills, salaries, and subscriptions that they have not manually entered into Arthsavora. The Pattern Detection engine analyzes historical transaction records to discover candidate recurring commitments, infer their cadences, score confidence, and surface recommendations for human confirmation.

---

## 2. Detection Algorithm & Clustering Pipeline

The detection pipeline operates in four deterministic stages:

```
    ┌────────────────────────────────────────────────────────┐
    │ 1. Transaction Ingestion & Filtering                   │
    │    • Filter workspace transactions (status='posted')   │
    │    • Exclude internal transfers & CC payments          │
    │    • Window: past 90 to 365 days                       │
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 2. Normalized Clustering                               │
    │    • Group by merchant_id OR normalized description    │
    │    • Sub-group by exact or approximate amount cluster  │
    │    • Minimum cluster size: >= 2 transactions           │
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 3. Cadence & Interval Analysis                         │
    │    • Sort occurrences chronologically                  │
    │    • Compute inter-arrival deltas (days)               │
    │    • Classify median delta:                            │
    │      - 6 to 8 days   -> 'weekly'                       │
    │      - 13 to 16 days -> 'biweekly'                     │
    │      - 27 to 32 days -> 'monthly'                      │
    │      - 85 to 95 days -> 'quarterly'                    │
    │      - 350 to 380 d  -> 'annual'                       │
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 4. Explainable Confidence Scoring                      │
    │    • Count weight (0.3): cluster size >= 3             │
    │    • Interval regularity (0.4): delta variance < 3 d   │
    │    • Amount consistency (0.3): variance < 5%           │
    └────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical Confidence Formulation

Let a cluster of $n$ transactions have sorted dates $t_1, t_2, \dots, t_n$ with intervals $\Delta_i = t_{i+1} - t_i$, and amounts $a_1, a_2, \dots, a_n$.

1. **Volume Score ($S_{\text{count}}$)**:
   $$S_{\text{count}} = \min\left(1.0, \frac{n}{4}\right)$$

2. **Interval Regularity Score ($S_{\text{interval}}$)**:
   Let $\sigma_{\Delta}$ be the standard deviation of inter-arrival intervals:
   $$S_{\text{interval}} = \max\left(0.0, 1.0 - \frac{\sigma_{\Delta}}{10.0}\right)$$

3. **Amount Regularity Score ($S_{\text{amount}}$)**:
   Let $\mu_a$ be the mean amount and $\sigma_a$ be the standard deviation:
   $$S_{\text{amount}} = \max\left(0.0, 1.0 - \frac{\sigma_a}{\mu_a}\right)$$

4. **Composite Confidence**:
   $$\text{Confidence} = 0.35 \times S_{\text{count}} + 0.35 \times S_{\text{interval}} + 0.30 \times S_{\text{amount}}$$

Only candidates with $\text{Confidence} \ge 0.60$ are surfaced to the user.

---

## 4. User In-The-Loop Governance

1. **No Silent Creation**: Suggestions are created in status `pending` in table `recurring_suggestions`.
2. **Review & Action**:
   - **Confirm**: The user approves the suggestion, creating an active `RecurringDefinition` (and optional `Subscription`), while marking the suggestion `confirmed`.
   - **Dismiss**: The user rejects the suggestion. It is marked `dismissed` to prevent repeated re-prompting.
3. **Traceability**: The reason for detection (sample transactions, inferred interval, amount variance) is serialized in `detection_reasons` for complete transparency.
