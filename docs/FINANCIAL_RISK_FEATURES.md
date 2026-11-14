# Arthsavora Financial Risk Features & Behavioral Profiling

## 1. Feature Engineering Overview

The Arthsavora risk intelligence system derives objective, explainable, and privacy-preserving numerical features from historical transaction books. These features characterize spending behavior without storing or transmitting sensitive Personal Identifiable Information (PII).

---

## 2. Risk Dimensions & Indicators

| Dimension | Primary Metric | Baseline Window | Description |
| :--- | :--- | :--- | :--- |
| **Amount Discrepancy** | Absolute Paise & Multiple of Median | 180 Days | Captures high-value transactions and extreme deviation from merchant-specific typical payments. |
| **Velocity / Frequency** | Count within Rolling Window | 30 Minutes | Tracks rapid successive card swipes or UPI payments at the same terminal or counterparty. |
| **Merchant Familiarity** | Historical Transaction Count | Lifetime / 180 Days | Evaluates whether a payee is new, occasional, or routine. |
| **Category Velocity** | Current Month vs Daily Baseline | 90 Days | Identifies sudden volume surges in discretionary categories (e.g., luxury shopping, nightlife). |
| **Commitment Adherence** | Percentage Variance to Expected | Scheduled Period | Detects unexpected subscription cost escalations or unauthorized debits on cancelled plans. |
| **Temporal Dispersion** | Hour-of-day & Weekend Flag | 90 Days | Models circadian spending patterns without inferring geolocation or private lifestyle habits. |
| **Ledger Reconciliation** | Statement vs Book Balance Delta | Statement Close | Uncovers unreconciled statement variances exceeding configured tolerance thresholds. |

---

## 3. Multivariate Feature Vector for Unsupervised ML

The unsupervised machine learning engine (`IsolationForest`) ingests a strictly normalized 5-dimensional numerical vector $\mathbf{x} \in \mathbb{R}^5$:

$$\mathbf{x} = \begin{bmatrix} x_{\text{amount\_log}} \\ x_{\text{merchant\_ratio}} \\ x_{\text{time\_delta}} \\ x_{\text{hour\_norm}} \\ x_{\text{is\_weekend}} \end{bmatrix}$$

1. **$x_{\text{amount\_log}} = \ln(1 + \text{amount}_{\text{INR}})$**:
   Logarithmic compression of rupee spend to stabilize heavy-tailed financial distributions.
2. **$x_{\text{merchant\_ratio}} = \min\left(10.0, \frac{\text{amount\_paise}}{\max(1, \text{median\_paise})}\right)$**:
   Ratio of current transaction to historical merchant median (capped at 10.0 to prevent runaway gradients).
3. **$x_{\text{time\_delta}} = \min\left(168.0, \Delta t_{\text{hours}}\right)$**:
   Hours elapsed since previous transaction in the workspace (capped at 1 week = 168 hours).
4. **$x_{\text{hour\_norm}} = \frac{\text{hour}}{24.0} \in [0.0, 1.0)$**:
   Normalized temporal indicator of the transaction timestamp.
5. **$x_{\text{is\_weekend}} \in \{0.0, 1.0\}$**:
   Binary indicator where Saturday or Sunday equals 1.0, otherwise 0.0.

---

## 4. Privacy & Governance Guarantees

- **No Raw Account Numbers or Credentials**: Features contain zero bank account credentials, PAN numbers, Aadhaar details, or card numbers.
- **No Free-Text Vector Embeddings**: Raw merchant names and notes are converted into deterministic numerical indicators (ratios, frequencies) to prevent inadvertent data leakage.
- **In-Memory Feature Synthesis**: Training matrices are computed in ephemeral memory on-the-fly and never persisted in unencrypted analytical warehouses.
