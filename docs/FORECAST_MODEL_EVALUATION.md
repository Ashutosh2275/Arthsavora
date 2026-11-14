# ARTHSAVORA — FORECAST MODEL EVALUATION AND ROLLING-ORIGIN VALIDATION
**Document Reference:** `docs/FORECAST_MODEL_EVALUATION.md`  
**Version:** 1.0.0  
**Status:** Active / Institutional Reference  
**Scope:** Stage 4 — Financial Forecasting, Cash-Flow Prediction and Predictive Intelligence [16]  
**Market:** India-First (Commercial FinTech Ecosystem)

---

## 1. Executive Summary

Standard k-fold cross-validation is invalid for financial time-series because shuffling observations introduces future lookahead leakage. To evaluate forecasting models rigorously, Arthsavora implements **Walk-Forward Rolling-Origin Cross-Validation** (also known as rolling-origin evaluation with expanding windows).

Every candidate algorithm is evaluated on out-of-sample predictions. An advanced model is promoted to production only if it statistically outperforms the transparent baseline; otherwise, the system automatically falls back to the simpler, more explainable model.

---

## 2. Walk-Forward Rolling-Origin Methodology

In walk-forward cross-validation, the training window iteratively expands from a minimum required history ($N_{\text{min\_train}} = 14$ days) up to the full series length $N$, stepping forward by a stride of $S = 7$ days.

```
Iteration 1: [==== Train (14 days) ====] -> [ Test (7 days) ]
Iteration 2: [======= Train (21 days) =======] -> [ Test (7 days) ]
Iteration 3: [========== Train (28 days) ==========] -> [ Test (7 days) ]
...
```

At each iteration $k$:
1. The model is trained **strictly on past data** up to origin $T_k$.
2. It generates out-of-sample forecasts for horizon $[T_k + 1, T_k + 7]$.
3. Forecast values $\hat{y}_t$ are compared against actual recorded expenditures $y_t$.
4. Prediction errors $e_t = \hat{y}_t - y_t$ and coverage indicator $I(L_t \le y_t \le U_t)$ are recorded.
5. The origin shifts forward by $S$ days.

This produces an unbiased, true out-of-sample assessment of real-world predictive accuracy.

---

## 3. Quantitative Evaluation Metrics

All evaluations compute five standardized financial accuracy metrics:

### 1. Mean Absolute Error (MAE in Paise)
Measures the average magnitude of prediction error in integer currency units:
$$\text{MAE} = \frac{1}{M} \sum_{t=1}^M |y_t - \hat{y}_t|$$

### 2. Root Mean Squared Error (RMSE in Paise)
Penalizes large errors disproportionately, revealing vulnerability to severe forecast misses:
$$\text{RMSE} = \sqrt{\frac{1}{M} \sum_{t=1}^M (y_t - \hat{y}_t)^2}$$

### 3. Weighted Absolute Percentage Error (WAPE)
Standard Mean Absolute Percentage Error (MAPE) fails in personal finance because actual daily spend is frequently 0 (leading to division-by-zero errors). WAPE provides a robust, scale-independent percentage error:
$$\text{WAPE} = \frac{\sum_{t=1}^M |y_t - \hat{y}_t|}{\sum_{t=1}^M y_t}$$
A WAPE of $0.15$ indicates that aggregate forecast error is $15\%$ of total spending volume.

### 4. Mean Forecast Bias (Paise)
Reveals systematic directional skew in the model:
$$\text{Bias} = \frac{1}{M} \sum_{t=1}^M (\hat{y}_t - y_t)$$
- $\text{Bias} > 0$: Overforecasting (systematically predicts higher expenses than incurred).
- $\text{Bias} < 0$: Underforecasting (systematically underestimates spending).
- $\text{Bias} \approx 0$: Well-calibrated, unbiased predictions.

### 5. Prediction Interval Coverage Probability (PICP)
Measures the empirical calibration of confidence intervals:
$$\text{Coverage} = \frac{1}{M} \sum_{t=1}^M \mathbf{1}_{\{L_t \le y_t \le U_t\}}$$
For an 80% confidence level, coverage should ideally land between $78\%$ and $85\%$. If coverage drops below $70\%$, the uncertainty bounds are under-dispersed.

---

## 4. Candidate Model Suite

| Model Identifier | Theoretical Foundation | Parameterization | Complexity |
| :--- | :--- | :--- | :---: |
| **`historical_mean`** | Baseline expectation over full window | $\hat{y} = \frac{1}{N}\sum y$ | Low / Transparent |
| **`moving_average`** | Local window run-rate | Window $= 7$ or $14$ days | Low |
| **`exponential_smoothing`** | Simple Exponential Smoothing (SES) | Level $\alpha = 0.3$ | Moderate |
| **`holt_winters`** | Additive level, trend, and weekly seasonality | $\alpha=0.3, \beta=0.1, \gamma=0.2, L=7$ | High |
| **`linear_trend`** | Damped slope ordinary least squares | Damping factor $\phi = 0.95$ | Moderate |

---

## 5. Automated Model Selection Algorithm

The engine selects the production model dynamically using the function `select_best_model`:

```python
def select_best_model(
    series: List[TimeSeriesPoint],
    candidate_models: Optional[List[str]] = None,
) -> Tuple[str, EvaluationMetricsVO]:
    best_model = "historical_mean"
    best_metrics = evaluate_time_series_walk_forward(series, model_name="historical_mean")

    for model_name in candidate_models:
        if model_name == "historical_mean":
            continue
        metrics = evaluate_time_series_walk_forward(series, model_name=model_name)
        
        # Rigorous Promotion Gate:
        # Candidate model must reduce WAPE by at least 2% relative to best model
        if metrics.wape < best_metrics.wape * 0.98:
            best_model = model_name
            best_metrics = metrics

    return best_model, best_metrics
```

### The 2% Complexity Hurdle Rule
To avoid overfitting and unnecessary algorithmic complexity, an advanced statistical model (e.g., Holt-Winters) is chosen **only if it reduces out-of-sample WAPE by at least 2%** compared to the simpler baseline. If the error improvement is negligible, Occam's razor prevails and the transparent baseline is retained.
