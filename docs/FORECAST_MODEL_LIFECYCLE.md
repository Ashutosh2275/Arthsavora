# ARTHSAVORA — FORECAST MODEL LIFECYCLE AND DRIFT MANAGEMENT
**Document Reference:** `docs/FORECAST_MODEL_LIFECYCLE.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Financial forecasting systems in production must handle continuous changes in consumer habits, macro-economic shifts (inflation, salary revisions), and sudden lifecycle changes (new jobs, moving apartments). Static models decay rapidly over time without active lifecycle governance.

The **Arthsavora Forecast Model Lifecycle Framework** governs model training, evaluation, automated promotion, serving, and graceful degradation across all active workspaces.

---

## 2. Model Lifecycle State Machine

```
┌─────────────────┐
│  Data Ingest &  │  Historical posted transactions extracted & contiguous
│  Preparation    │  series constructed by DataPreparationService
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Eligibility│  Check active transaction density (sufficient / limited / insufficient)
│ Assessment      │
└────────┬────────┘
         │
         ├───────────────────────[ Active days < 7 ]────────────────────────┐
         │                                                                  │
         ▼                                                                  ▼
┌─────────────────┐                                                ┌─────────────────┐
│ Rolling-Origin  │  Walk-forward validation over candidate models │  Baseline Fall- │
│ Evaluation      │  (Mean, MA, SES, Holt-Winters, Linear Trend)   │  back Engine    │
└────────┬────────┘                                                └────────┬────────┘
         │                                                                  │
         ▼                                                                  │
┌─────────────────┐                                                         │
│ Automated Model │  Selects candidate with lowest WAPE                     │
│ Selection       │  (Must beat baseline by >= 2%)                          │
└────────┬────────┘                                                         │
         │                                                                  │
         ▼                                                                  │
┌─────────────────┐                                                         │
│ Serving & Run   │◄────────────────────────────────────────────────────────┘
│ Persistence     │  Persists forecast_runs, forecast_points, evaluations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Drift Monitoring│  Detects structural breaks or prediction misses
│ & Retraining    │  (Scheduled weekly or triggered by major statement imports)
└─────────────────┘
```

---

## 3. Retraining Triggers & Scheduling

Forecast models are never trained once and left static. They are re-evaluated and refreshed according to strict policies:

### 1. Temporal Schedule
- Standard rolling forecasts are re-generated on a weekly cadence (or daily when viewing active cash-flow dashboards).
- Historical lookback defaults to 90 days, capturing recent velocity while pruning obsolete seasonal spikes.

### 2. Event-Driven Triggers
- **Statement Import Completion (Prompt 11):** When a user imports a CSV/PDF bank statement containing $>10$ posted transactions, previous forecast runs are marked superseded and a fresh model evaluation is queued.
- **Budget Adjustments (Prompt 14):** Changes to category allocations or spending limits re-trigger budget exhaustion models.
- **Recurring Commitment Modifications (Prompt 15):** Adding or canceling a subscription, loan EMI, or salary schedule updates the cash-flow trajectory instantly.

---

## 4. Graceful Degradation Hierarchy

If an error or mathematical anomaly occurs during execution (e.g., zero matrix determinant, infinite gradient, or invalid variance), the engine executes an orderly, tiered fallback:

```
Tier 1: Advanced Statistical / Seasonality Model (Holt-Winters)
   │
   ▼ (if non-convergent, numerical error, or WAPE degradation)
Tier 2: Moving Average Model (7-day or 14-day localized run rate)
   │
   ▼ (if window contains insufficient variance or zero entries)
Tier 3: Historical Mean Model (Total spending volume divided by observation days)
   │
   ▼ (if total active days < 7)
Tier 4: Transparent Insufficient Data Mode (Flagged without hallucinating numbers)
```

At no point does the system throw an unhandled 500 error or return fabricated data points. Every fallback is explicitly recorded in `forecast_runs.model_name` and `metadata_["fallback_reason"]`.

---

## 5. Model Versioning & Traceability

Every forecast execution creates an immutable audit trail:
- `forecast_runs.model_name`: Identifies the active algorithm (e.g., `holt_winters`, `exponential_smoothing`, `historical_mean`).
- `forecast_runs.model_version`: Semantic version identifier (`v1.0.0`).
- `forecast_runs.data_quality_score`: Numerical score reflecting data integrity.
- `forecast_evaluations`: Detailed validation metrics (`mae_paise`, `rmse_paise`, `wape`, `bias_paise`, `interval_coverage`) recorded per run.

This metadata enables users and auditors to verify exactly how a prediction was generated and assess its historical reliability.
