# ARTHSAVORA — DETERMINISTIC FINANCIAL SCENARIO ENGINE
**Document Reference:** `docs/FINANCIAL_SCENARIO_ENGINE.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Users require the ability to simulate financial outcomes before making major life decisions: *"What happens if I get a 15% raise?", "What if rent increases by ₹5,000 next month?", "Can I afford to purchase a ₹1,20,000 laptop on December 15th without running out of cash?"*

The **Arthsavora Financial Scenario Engine** (`ScenarioService` & `evaluate_scenario`) provides a completely deterministic, side-by-side "what-if" simulation platform. It takes a baseline forecast and applies hypothetical modifications—such as proportional adjustments or lump-sum one-time items—to project alternative balance curves and liquidity trajectories.

Crucially, scenarios are **strictly hypothetical sandboxes**. They never mutate the general ledger, posted transactions, bank accounts, or budget records.

---

## 2. Standard Scenario Archetypes

The platform supports four standardized scenario configurations:

| Scenario Archetype | Income Adjustment | Expense Adjustment | Typical Use Case |
| :--- | :---: | :---: | :--- |
| **`baseline`** | $1.00$ ($0\%$) | $1.00$ ($0\%$) | Current trajectory based on historical velocity and confirmed recurring schedules. |
| **`optimistic`** | $1.10$ ($+10\%$) | $0.95$ ($-5\%$) | Career advancement, freelance bonus, or disciplined lifestyle frugal adjustments. |
| **`conservative`** | $0.90$ ($-10\%$) | $1.10$ ($+10\%$) | Inflationary pressures, reduced work hours, medical emergency, or economic stress testing. |
| **`custom`** | User-defined | User-defined | Specific personal life events (buying a vehicle, home renovation, wedding, career pivot). |

---

## 3. Mathematical Simulation Mechanics

Given a baseline timeline of $H$ days with daily inflows $\text{In}_t$, outflows $\text{Out}_t$, and initial starting balance $B_0$:

### 1. Multiplier Scaling
Discretionary inflows and outflows are scaled by user-defined multipliers:
$$\widetilde{\text{In}}_t = \text{round}\left( \text{In}_t \times M_{\text{income}} \right)$$
$$\widetilde{\text{Out}}_t = \text{round}\left( \text{Out}_t \times M_{\text{expense}} \right)$$

### 2. Lump-Sum One-Time Inflows & Outflows
Users can inject discrete one-time hypothetical capital events on specific future dates:
- $\Omega_{\text{in}, t}$: Sum of all one-time lump-sum inflows scheduled on date $t$ (e.g., annual performance bonus, tax refund, gift).
- $\Omega_{\text{out}, t}$: Sum of all one-time lump-sum outflows scheduled on date $t$ (e.g., insurance annual premium, down payment, equipment purchase).

### 3. Net Daily Flow & Running Balance
$$\text{Simulated Inflow}_t = \widetilde{\text{In}}_t + \Omega_{\text{in}, t}$$
$$\text{Simulated Outflow}_t = \widetilde{\text{Out}}_t + \Omega_{\text{out}, t}$$
$$\text{Simulated Net}_t = \text{Simulated Inflow}_t - \text{Simulated Outflow}_t$$
$$\text{Simulated Balance}_t = \text{Simulated Balance}_{t-1} + \text{Simulated Net}_t$$

---

## 4. Scenario Entity Relational Model

Scenarios are persisted in PostgreSQL table `financial_scenarios` for persistent tracking, comparison, and team/family review:

```python
class FinancialScenario(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "financial_scenarios"

    workspace_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scenario_type: Mapped[str] = mapped_column(String(50), default="custom", nullable=False)  # baseline, optimistic, conservative, custom
    
    # Proportional parameters
    income_multiplier: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)
    expense_multiplier: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1.0000"), nullable=False)
    
    # Discrete events stored in JSONB
    one_time_inflows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    one_time_outflows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Simulation Results
    simulated_ending_balance_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    simulated_net_cash_flow_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    simulation_results: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
```

---

## 5. Comparative Delta Analytics

When a scenario is simulated against the baseline, the engine computes delta metrics:
- **Ending Balance Delta:** $\Delta_B = \text{Simulated Ending Balance} - \text{Baseline Ending Balance}$
- **Net Cash Flow Delta:** $\Delta_{\text{flow}} = \text{Simulated Net Flow} - \text{Baseline Net Flow}$
- **Trough Difference:** Evaluates whether the scenario introduces new liquidity shortfalls or remedies existing troughs.

This information is presented in the UI in side-by-side comparison tables and dual-line timeline graphs, allowing users to make informed, risk-adjusted decisions.
