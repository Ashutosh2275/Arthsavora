# ARTHSAVORA — FINANCIAL FORECASTING ARCHITECTURE
**Document Reference:** `docs/FORECASTING_ARCHITECTURE.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary & Objective

The **Arthsavora Financial Forecasting Engine** delivers mathematically grounded, explainable, and privacy-preserving forward-looking financial intelligence for personal, family, and small-business workspaces. 

Forecasting in Arthsavora is governed by strict institutional financial principles:
1. **Forecasts are informational estimates, never guaranteed financial outcomes.** They provide probabilistic projections with transparent confidence bounds (80%, 95%) to empower proactive budgeting and cash management.
2. **Strict separation between actuals, commitments, and estimates:**
   - **Historical Facts:** Immutable, posted transactions and double-entry general ledger journal entries.
   - **Scheduled Commitments (Prompt 15):** Known, verified recurring obligations (e.g., salary deposits, rent payments, loan EMIs, insurance premiums).
   - **Statistical Predictions:** Algorithmic estimates derived from historical velocity, trend lines, and seasonal cadence.
   - **Hypothetical Assumptions:** User-defined "what-if" scenario parameters (e.g., ±10% income changes, planned capital expenditures).
3. **Zero Ledger Mutations:** Forecasting routines **never mutate** the general ledger, account balances, transaction ledgers, or budget allocations. All calculations remain strictly read-only and non-destructive.
4. **Exact Monetary Precision:** All internal storage and computation utilize exact 64-bit integer minor units (`paise`) and fixed-point `NUMERIC(18, 4)`. Floating-point numbers are strictly banned from balance calculations.

---

## 2. High-Level Architecture & Component Topology

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 ARTHSAVORA WEB CLIENT                                  │
│  (Zustand Store: useForecastStore | Timeline Chart | Scenarios | Exhaustion | Goals)   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP / JSON API (v1/forecasts)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  FASTAPI API LAYER                                     │
│  - Endpoint Authentication & Workspace Context                                        │
│  - Permission Enforcement: forecasts:view, forecasts:manage                           │
│  - Pydantic DTO Serialization with Exact Decimal / Paise Precision                     │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION SERVICES LAYER                                │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌───────────────────────────┐  │
│  │   ForecastingService   │  │    ScenarioService     │  │ BudgetExhaustionService   │  │
│  │ (Pipeline & Model Run) │  │  (What-If Simulations) │  │  (Burn Rate & Exhaustion) │  │
│  └───────────┬────────────┘  └───────────┬────────────┘  └─────────────┬─────────────┘  │
│              │                           │                             │                │
│              ▼                           ▼                             ▼                │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌───────────────────────────┐  │
│  │  DataPrepService       │  │ GoalProjectionService  │  │ Automated Model Selector  │  │
│  │ (Liquid Balance/Series)│  │ (Savings Pace/Velocity)│  │ (Rolling-Origin Cross-Val)│  │
│  └───────────┬────────────┘  └───────────┬────────────┘  └─────────────┬─────────────┘  │
└──────────────┼───────────────────────────┼─────────────────────────────┼────────────────┘
               ▼                           ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              DOMAIN FORECASTING ENGINE                                 │
│  - Data Eligibility & Quality Scoring (Non-fabricating validation)                    │
│  - Candidate Models: Historical Mean, Moving Average, Exponential Smoothing,          │
│    Holt-Winters (Weekly Seasonality), Linear Trend (Damped Slope)                     │
│  - Walk-Forward Validation Engine: MAE, RMSE, WAPE, Bias, Interval Coverage           │
│  - Cash-Flow Trajectory Engine: Double-counting prevention with Prompt 15 Occurrences  │
│  - Confidence Intervals: 80% (z=1.28) & 95% (z=1.96) with Horizon Uncertainty Drift │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               REPOSITORY & DATABASE LAYER                              │
│  - ForecastRepository (PostgreSQL 18 Multi-Tenant Workspace-Scoped Access)             │
│  - Tables: forecast_runs, forecast_points, financial_scenarios, forecast_evaluations  │
│  - Transaction, Account, RecurringDefinition, Budget, FinancialGoal Reads             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Engine Invariants

### Invariant 1: Cash-Flow Projection Equation
For any projected date $t$ within the forecast horizon $[1, H]$:
$$\text{Projected Balance}_t = \text{Balance}_{t-1} + \text{Inflow}_t - \text{Outflow}_t$$
where:
$$\text{Inflow}_t = \text{Recurring Inflow}_t + \max(0, \text{Discretionary Statistical Inflow}_t - \text{Recurring Inflow}_t)$$
$$\text{Outflow}_t = \text{Recurring Outflow}_t + \max(0, \text{Discretionary Statistical Outflow}_t - \text{Recurring Outflow}_t)$$

This formulation strictly prevents **double counting** scheduled recurring obligations that are already captured in statistical historical averages.

### Invariant 2: Uncertainty Monotonicity
Because forecast uncertainty compounds over time, the confidence interval width $W_t = \text{Upper}_t - \text{Lower}_t$ must satisfy:
$$W_t \ge W_{t-1} \quad \text{for all } t \ge 1$$
This is guaranteed by the step expansion factor $\sqrt{1 + \frac{t}{\lambda}}$ applied across residual standard errors.

### Invariant 3: Bounded Balance Interval Invariant
On every step $t$:
$$\text{Lower Balance}_t \le \text{Projected Balance}_t \le \text{Upper Balance}_t$$
The lower bound reflects the worst-case scenario (minimum discretionary inflow and maximum discretionary outflow combined with deterministic commitments), while the upper bound reflects the optimal scenario.

### Invariant 4: Non-Fabrication Rule
When historical transaction data is sparse ($< 7$ active days with transactions), the system **must never synthesize imaginary transaction points**. Instead, it flags the workspace as `"insufficient_data"`, transparently falls back to a simple historical mean, and alerts the user to import additional records.

---

## 4. Multi-Tenant Isolation & Role-Based Access Control

All forecasting entities (`forecast_runs`, `forecast_points`, `financial_scenarios`, `forecast_evaluations`) enforce foreign-key cascading isolation scoped directly by `workspace_id`. Cross-workspace reads or writes are prevented by repository-level tenancy validation:

```python
stmt = select(ForecastRun).where(
    ForecastRun.id == run_id,
    ForecastRun.workspace_id == workspace_id,
    ForecastRun.is_deleted == False,
)
```

### Permission Matrix

| Role | `forecasts:view` | `forecasts:manage` | Description |
| :--- | :---: | :---: | :--- |
| **Owner** | Yes | Yes | Full control over runs, scenarios, parameters, and evaluations |
| **Admin** | Yes | Yes | Can generate forecasts, run scenario simulations, manage parameters |
| **Member** | Yes | No | Can view timelines, projections, scenarios, and exhaustion dates |
| **Viewer** | Yes | No | Read-only access to published forecast dashboards |

---

## 5. Summary of Related Technical Documentation

- Data extraction and cleaning protocols: [`docs/FINANCIAL_DATA_PREPARATION.md`](file:///d:/Arthsavora/docs/FINANCIAL_DATA_PREPARATION.md)
- Income and expense modeling: [`docs/INCOME_EXPENSE_FORECASTING.md`](file:///d:/Arthsavora/docs/INCOME_EXPENSE_FORECASTING.md)
- Cash-flow and balance trajectory: [`docs/CASH_FLOW_FORECASTING.md`](file:///d:/Arthsavora/docs/CASH_FLOW_FORECASTING.md)
- Model evaluation and rolling-origin cross-validation: [`docs/FORECAST_MODEL_EVALUATION.md`](file:///d:/Arthsavora/docs/FORECAST_MODEL_EVALUATION.md)
- Uncertainty quantification and confidence intervals: [`docs/FORECAST_UNCERTAINTY.md`](file:///d:/Arthsavora/docs/FORECAST_UNCERTAINTY.md)
- Deterministic what-if scenario engine: [`docs/FINANCIAL_SCENARIO_ENGINE.md`](file:///d:/Arthsavora/docs/FINANCIAL_SCENARIO_ENGINE.md)
- Model lifecycle and fallback mechanisms: [`docs/FORECAST_MODEL_LIFECYCLE.md`](file:///d:/Arthsavora/docs/FORECAST_MODEL_LIFECYCLE.md)
- Privacy, data security, and compliance: [`docs/FORECAST_PRIVACY_SECURITY.md`](file:///d:/Arthsavora/docs/FORECAST_PRIVACY_SECURITY.md)
