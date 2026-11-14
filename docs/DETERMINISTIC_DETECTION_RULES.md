# Arthsavora Deterministic Anomaly Detection Rules

## 1. Purpose & Guarantees

Deterministic rules provide instantaneous, explainable, and zero-latency detection of clear financial anomalies. These rules operate without requiring historical sample sizes or training iterations.

Every rule produces a structured `AnomalyEvidenceVO` containing exact mathematical thresholds, observed values, and human-readable explanations.

---

## 2. Standard System Default Rules

| Rule Code | Category | Default Severity | Default Threshold | Description & Logic |
| :--- | :--- | :--- | :--- | :--- |
| `RULE_HIGH_AMOUNT` | `amount` | `high` / `critical` | ₹50,000 (5,000,000 paise) | Flags single transactions exceeding user-configured or institutional spending ceiling. Escalates to `critical` if amount $\ge 2\times$ threshold. |
| `RULE_FREQUENCY_BURST` | `frequency` | `high` | 3 tx in 30 minutes | Flags rapid multi-transaction velocity to the same merchant within a rolling 30-minute window. |
| `RULE_RECURRING_HIKE` | `recurring` | `medium` | >15% and $\ge$ ₹500 hike | Flags recurring debit where actual charge exceeds expected subscription amount by more than 15% and at least ₹500. |
| `RULE_CANCELLED_RECURRING` | `recurring` | `critical` | Any debit | Flags financial transactions charged against subscriptions or commitments marked cancelled or inactive. |
| `RULE_DUPLICATE_CANDIDATE` | `duplicate` | `medium` | Exact amount within 48h | Identifies potential accidental double-swipes or double-billing with the same amount, merchant, and account within 48 hours. |
| `RULE_BALANCE_DISCREPANCY` | `account` | `high` | > ₹1,000 (100,000 paise) | Flags discrepancies between verified external statement balance and derived book balance in double-entry accounts. |

---

## 3. Dynamic Threshold Customization & Workspace Overrides

Workspaces can customize any deterministic rule without affecting system defaults:
- **Inheritance Pattern**: System default rules have `workspace_id IS NULL`. When a user updates a rule threshold or toggles `is_enabled`, the system automatically forks a workspace-specific override row (`workspace_id = current_workspace_id`).
- **Precedence**: Queries fetch rules where `workspace_id = :id OR workspace_id IS NULL`. Custom overrides take precedence over system defaults via priority deduplication.

---

## 4. Rule Execution Semantics

```python
# Evaluates candidate transaction against active workspace rules
evidences = evaluate_deterministic_rules(
    tx=candidate_vo,
    rules=active_rules,
    recent_transactions=recent_window_txs,
    recurring_info=matched_recurring_definition,
)
```

Each rule executes functionally with zero side-effects. If a candidate triggers multiple deterministic conditions (e.g., both high amount and frequency burst), both are collected as independent evidence objects and subsequently synthesized by the multi-signal hybrid engine.
