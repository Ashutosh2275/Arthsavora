# ARTHSAVORA — FORECAST PRIVACY, DATA PROTECTION AND SECURITY
**Document Reference:** `docs/FORECAST_PRIVACY_SECURITY.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Financial forecasting processes deeply personal, sensitive data: bank balances, income schedules, rent obligations, loan debts, and discretionary spending habits. In an era where unvetted cloud AI models ingest proprietary user records for model training, Arthsavora adheres to an unwavering privacy commitment:

**All financial forecasting, time-series analysis, walk-forward evaluations, and scenario simulations run strictly within the secure application boundary.** Private transaction records are never transmitted to third-party AI APIs, cloud LLM vendors, or unauthorized external telemetry.

---

## 2. In-Boundary Computation Guarantee

1. **Local Deterministic Runtimes:** All mathematical routines (`historical_mean`, `moving_average`, `exponential_smoothing`, `holt_winters`, `linear_trend`, and walk-forward cross-validation) execute in Python using pure in-memory vectorized calculations.
2. **Zero Third-Party Model Training:** User spending data is never used to train generalized multi-tenant models or shared with external parties.
3. **No Unencrypted Network Hops:** All calculations take place in the backend application worker adjacent to the PostgreSQL database, eliminating external network attack surfaces.

---

## 3. Multi-Tenant Isolation & Anti-IDOR Protections

Every forecast entity (`forecast_runs`, `forecast_points`, `financial_scenarios`, `forecast_evaluations`) is strictly partitioned by `workspace_id`.

### Repository Tenancy Checks
All read, update, simulation, and delete operations execute tenant-scoped queries:
```python
stmt = select(FinancialScenario).where(
    FinancialScenario.id == scenario_id,
    FinancialScenario.workspace_id == workspace_id,
    FinancialScenario.is_deleted == False,
)
```
Attempting to reference a scenario or forecast run belonging to another workspace returns a `404 Not Found` (or `403 Forbidden`), completely preventing Insecure Direct Object Reference (IDOR) exploits.

---

## 4. Role-Based Access Control (RBAC)

Two specialized forecasting permissions govern access:
- `Permission.VIEW_FORECASTS = "forecasts:view"`: Grants read access to historical forecast runs, cash-flow timelines, category forecasts, budget exhaustion estimates, and scenario comparative views.
- `Permission.MANAGE_FORECASTS = "forecasts:manage"`: Grants permission to trigger new forecast generation runs, create or delete financial scenarios, and execute what-if simulations.

### Workspace Role Assignment
- **Personal Workspace:** The owner holds both `VIEW_FORECASTS` and `MANAGE_FORECASTS`.
- **Family Workspace:** Head of household holds `MANAGE_FORECASTS`; family members hold `VIEW_FORECASTS`.
- **Business Workspace:** Owners, Partners, and Accountants hold `MANAGE_FORECASTS`; Employees hold restricted or no access.

---

## 5. Audit Logging & Traceability

Every operation modifying forecasting state is captured in the immutable audit log:
- `forecast.run.generated`: Workspace, user, horizon, model selected, WAPE score.
- `scenario.created` / `scenario.updated` / `scenario.deleted`: Scenario name, parameter adjustments, user ID.
- `scenario.simulated`: Scenario ID, simulated ending balance, delta against baseline.

Audit logs record the actor, timestamp, IP address, user-agent, and workspace ID, ensuring full institutional auditability.

---

## 6. Data Retention & Purge Policies

- **Soft Deletion:** Scenarios and forecast runs employ `is_deleted = TRUE` flags (`SoftDeleteMixin`) to prevent accidental data loss.
- **Cascade Deletion:** When a workspace is deleted by its owner, foreign key constraints (`ON DELETE CASCADE`) guarantee that all associated `forecast_runs`, `forecast_points`, `financial_scenarios`, and `forecast_evaluations` are completely purged from disk without orphaned data fragments.
- **Historical Pruning:** Obsolete daily forecast points from runs older than 180 days can be safely pruned during routine maintenance windows, retaining only the summary `forecast_runs` metadata.
