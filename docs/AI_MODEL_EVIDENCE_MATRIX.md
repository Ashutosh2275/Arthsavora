# AI Model Evidence Matrix

## 1. Overview

This matrix inventories every machine learning model, statistical algorithm, and NLP heuristic deployed within ARTHSAVORA, detailing their implementation libraries, hyperparameters, input features, and verification evidence.

---

## 2. Model Inventory & Parameter Specifications

### 2.1 Transaction Categorization Classifier
- **Model Type:** Scikit-Learn Pipeline (`TfidfVectorizer` + `LogisticRegression`)
- **Source File:** `backend/app/services/intelligence/ml_classifier.py`
- **Hyperparameters:**
  - `TfidfVectorizer`: `ngram_range=(1, 2)`, `sublinear_tf=True`, `max_features=5000`
  - `LogisticRegression`: `C=1.0`, `solver="lbfgs"`, `max_iter=1000`, `multi_class="multinomial"`
- **Input Features:** Cleaned transaction description, merchant normalized name, transaction direction (`debit`/`credit`).
- **Output:** Predicted category slug, confidence score $[0.0, 1.0]$, confidence band (`HIGH`, `MEDIUM`, `LOW`), probability vector.
- **Explainability:** Returns top supporting n-gram tokens and probability mass.
- **Test File:** `backend/tests/test_categorization_service.py`

### 2.2 Cash Flow Time-Series Forecasting
- **Model Type:** Holt-Winters Exponential Smoothing & Linear Regression
- **Source File:** `backend/app/domain/forecasting.py`, `backend/app/services/forecasting/forecasting_service.py`
- **Components:**
  - Level ($\alpha = 0.2$), Trend ($\beta = 0.1$), Seasonal ($\gamma = 0.1$, period = 30 days)
  - Historical Mean & Weighted Moving Average baselines
- **Model Selection Metric:** Mean Absolute Scaled Error (MASE) / MAPE
- **Input Features:** Historical daily net cash flows, confirmed recurring obligations (`RecurringDefinition`).
- **Output:** Predicted daily cash balances with 80% and 95% confidence intervals for $T \in [1, 90]$ days.
- **Test File:** `backend/tests/test_forecast_service.py`

### 2.3 Financial Anomaly & Outlier Detector
- **Model Type:** Hybrid Statistical Outlier Engine (Z-Score + IQR) & Isolation Forest
- **Source File:** `backend/app/domain/anomaly.py`, `backend/app/services/anomaly/detection_service.py`
- **Parameters:**
  - Z-Score Threshold: $> 2.5\sigma$
  - IQR Multiplier: $1.5 \times \text{IQR}$ over 90-day category baseline
  - Velocity Window: $\ge 3$ transactions to same merchant within 15 minutes
- **Input Features:** Transaction amount (paise), category, merchant historical distribution, timestamp.
- **Output:** `AnomalyEvidenceVO` containing deviation score, anomaly type, and severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Test File:** `backend/tests/test_anomaly_service.py`

### 2.4 Document Extraction & Regex OCR Parser
- **Model Type:** Deterministic Pattern Matcher & Binary Magic Bytes Validator
- **Source File:** `backend/app/services/document/field_extractor.py`, `document_service.py`
- **Patterns:**
  - Indian GSTIN: `\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b`
  - Total Invoice Amount: Minor unit paise extraction with currency symbol matching
  - Invoice Date: ISO-8601, DD/MM/YYYY, and DD-Mon-YYYY patterns
- **Validation:** Binary magic byte header checks before parsing
- **Test File:** `backend/tests/test_document_service.py`

### 2.5 Natural Language Assistant Intent Parser
- **Model Type:** Rule-Guided Semantic Intent Classifier & Prompt Sanitizer
- **Source File:** `backend/app/services/assistant/sanitizer.py`, `assistant_service.py`
- **Supported Intents:** `GET_BALANCE`, `LIST_EXPENSES`, `ANALYZE_SPENDING`, `CHECK_BUDGET`, `EXPLAIN_TRANSACTION`
- **Safety Boundary:** Strict read-only query generation; no mutations permitted.
- **Test File:** `backend/tests/test_assistant_service.py`

---

## 3. Training & Validation Governance

- **Data Privacy:** Models train strictly on synthetic datasets or workspace-isolated tenant feedback. Zero cross-workspace training leakage.
- **Reproducibility:** Seeded random state (`random_state=42`) used across all scikit-learn models.
- **Persistence:** Serialized via `joblib` with cryptographic sha256 checksum validation upon model artifact load.
