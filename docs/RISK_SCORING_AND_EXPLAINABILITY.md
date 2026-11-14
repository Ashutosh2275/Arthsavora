# Arthsavora Risk Scoring, Hybrid Synthesis & Explainability

## 1. Hybrid Evidence Fusion

A transaction can trigger multiple detectors simultaneously (e.g., both a deterministic high-value rule and a statistical MAD merchant outlier). Rather than creating fragmented, duplicate alerts, the **Hybrid Synthesis Engine** fuses multiple signals into a single coherent anomaly record.

### Fusion Algorithm & Multi-Detector Reinforcement Boost

1. **Base Score Selection:**
   $$\text{Base Score} = \max_{e \in E}(\text{evidence.risk\_score})$$
   The primary severity and classification are anchored to the highest-confidence signal.

2. **Multi-Detector Reinforcement Boost:**
   When independent detection methods concur on an anomalous event, confidence increases:
   $$\text{Unique Methods} = \|\{e.\text{method} : e \in E\}\|$$
   $$\text{Boost} = (\text{Unique Methods} - 1) \times 5\text{ points}$$
   $$\text{Final Score} = \min(100, \text{Base Score} + \text{Boost})$$

3. **Composite Explanation Synthesis:**
   Primary explanations are presented first, followed by secondary corroborating evidence:
   `"Transaction amount of ₹75,000.00 exceeds your high-value threshold of ₹50,000.00. Corroborating signals: Amount of ₹75,000.00 is 4.2x higher than your historical median."`

---

## 2. Risk Score Tiers & Severity Spectrum

The risk score is mapped to standard institutional severity levels:

| Score Range | Severity Tier | Visual Badge | Typical Actions & Notification |
| :--- | :--- | :--- | :--- |
| **0 – 29** | Informational | Slate Gray | Informational log; no banner; silent digest. |
| **30 – 49** | Low | Blue | Low-priority badge in feed; review at leisure. |
| **50 – 69** | Medium | Amber / Yellow | Medium-priority badge; highlighted in weekly review. |
| **70 – 84** | High | Orange / Red | High-priority card; in-app banner; email digest. |
| **85 – 100** | Critical | Purple / Crimson | Urgent badge; immediate user push/SMS notification. |

---

## 3. Explainability Invariants

Every detected anomaly presented to the user must answer three mandatory questions:
1. **What was observed?** (e.g., `₹12,000 payment to Artisan Cafe`).
2. **Why was it flagged?** (e.g., `4.8x higher than historical median of ₹2,500`).
3. **What is the baseline comparison?** (e.g., `Based on 14 previous payments across 90 days`).

Alarmist, accusatory, or speculative words (such as *"fraudster"*, *"theft"*, *"compromised"*, *"hacked"*) are strictly prohibited from all generated explanations and system responses.
