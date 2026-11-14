# ARTHSAVORA — FORECAST UNCERTAINTY AND CONFIDENCE INTERVALS
**Document Reference:** `docs/FORECAST_UNCERTAINTY.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

A single point forecast (e.g., *"Your spending next month will be ₹42,500"*) is fundamentally incomplete and misleading. Real-world financial flows are subject to volatility, unexpected emergencies, variable utility bills, and discretionary spontaneity.

The **Arthsavora Forecast Uncertainty Framework** quantifies probabilistic dispersion across all predictions. Every point estimate $\hat{y}_t$ is accompanied by calibrated **lower bounds** and **upper bounds** at standard financial confidence levels (80% and 95%), visualized in the frontend as an expanding "uncertainty cone".

---

## 2. Confidence Levels & Critical Values

Standard normal critical values ($z$-scores) are utilized based on the requested confidence level:

| Confidence Level ($\gamma$) | Critical Value ($z$) | Empirical Meaning | Primary Use Case |
| :---: | :---: | :--- | :--- |
| **80%** | $1.282$ | 8 out of 10 outcomes fall within the band; tighter, practical range | Default planning view |
| **95%** | $1.960$ | 19 out of 20 outcomes fall within the band; wide conservative range | Conservative / Risk-averse stress testing |

---

## 3. Residual Variance & Error Estimation

Let $\{y_1, y_2, \dots, y_N\}$ be historical observations and $\{\hat{y}_1, \dots, \hat{y}_N\}$ be the fitted in-sample model estimates. The residual error on step $i$ is:
$$e_i = y_i - \hat{y}_i$$

The sample standard error of residuals $s_e$ is derived as:
$$s_e = \sqrt{\frac{1}{N - p} \sum_{i=1}^N e_i^2}$$
where $p$ is the number of estimated model parameters.

If history is limited or uniform, a safety floor of $s_e = \max(s_e, 0.20 \times \bar{y})$ is enforced to prevent unrealistically zero-width bands.

---

## 4. Horizon Uncertainty Expansion (The Fan Effect)

Uncertainty is not static across time. Predicting tomorrow's spending is substantially more certain than predicting spending 60 days in the future. As the lead step $k$ increases, compounding variance is modeled via a horizon expansion multiplier:

$$\sigma_k = s_e \cdot \sqrt{1 + \frac{k}{\lambda}}$$

where:
- $k \in [0, H-1]$ is the forward step index.
- $\lambda$ is the memory retention horizon (typically 10 for moving averages, or calibrated to smoothing parameter $\alpha$).

The step-specific margin of error $M_k$ is:
$$M_k = \text{round}\left( z \cdot \sigma_k \right)$$

### Lower and Upper Point Bounds
For an individual expenditure forecast point:
$$\text{Lower}_k = \max(0, \hat{y}_k - M_k)$$
$$\text{Upper}_k = \hat{y}_k + M_k$$

Because monetary expenditures cannot be negative, lower bounds are strictly floored at 0 paise.

---

## 5. Balance Trajectory Uncertainty & Invariant Preservation

In cumulative cash-flow forecasting, uncertainties in daily inflows and daily outflows compound into the running balance.

### Worst-Case vs. Best-Case Liquidity
At day $t$:
- **Worst-Case Flow (Min Inflow, Max Outflow):**
  $$\Delta_{\text{worst}} = \text{Inflow}_{\text{lower}, t} - \text{Outflow}_{\text{upper}, t} = (\text{Inflow}_t - \text{Margin}_{\text{in}, t}) - (\text{Outflow}_t + \text{Margin}_{\text{out}, t})$$
  $$\Delta_{\text{worst}} = \text{Net Flow}_t - (\text{Margin}_{\text{in}, t} + \text{Margin}_{\text{out}, t})$$
- **Best-Case Flow (Max Inflow, Min Outflow):**
  $$\Delta_{\text{best}} = \text{Inflow}_{\text{upper}, t} - \text{Outflow}_{\text{lower}, t} = (\text{Inflow}_t + \text{Margin}_{\text{in}, t}) - (\text{Outflow}_t - \text{Margin}_{\text{out}, t})$$
  $$\Delta_{\text{best}} = \text{Net Flow}_t + (\text{Margin}_{\text{in}, t} + \text{Margin}_{\text{out}, t})$$

### Monotonic Balance Bounds
Because deterministic recurring commitments (Prompt 15) carry zero margin of error, margin is added only from discretionary variance. Consequently:
$$\Delta_{\text{worst}} \le \text{Net Flow}_t \le \Delta_{\text{best}}$$
and accumulated across steps:
$$\text{Lower Balance}_t \le \text{Projected Balance}_t \le \text{Upper Balance}_t$$

This mathematical guarantee ensures that the projected balance trajectory never leaks outside its confidence interval envelope.
