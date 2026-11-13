# ARTHSAVORA — EXISTING IMPLEMENTATION INVENTORY
**Document Reference:** `docs/EXISTING_IMPLEMENTATION_INVENTORY.md`  
**Audit Baseline:** Commit `6caa716456ec7cd9fff31ab16ee4a929b9f1d710`  
**Date:** 2026-11-14  

This inventory catalogs every major software module discovered in the Arthsavora repository, detailing its current purpose, functional capabilities, internal/external dependencies, testing coverage, identified engineering issues, and planned evolution across the 30-prompt programme.

---

## 1. BACKEND MODULES

### MOD-BE-01: Application Root & Middleware
- **Module Name:** Core Application Engine
- **File Paths:**
  - `backend/app/main.py`
  - `backend/app/core/limiter.py`
  - `backend/app/core/config.py`
- **Current Purpose:** Bootstraps the FastAPI application instance, configures slowapi rate limiting, registers HTTP request auditing middleware, configures CORS, and binds API sub-routers.
- **Existing Functionality:**
  - Lifespan management for database connection startup and shutdown.
  - SlowAPI rate limit handler returning HTTP 429.
  - Request execution time auditing logged to stdout via Python `logging`.
  - Health check endpoint `GET /` returning status and version `1.1.0`.
- **Dependencies:** `fastapi`, `slowapi`, `motor`, `pydantic-settings`, `logging`.
- **Tests:** None (0% test coverage).
- **Known Issues:**
  - Insecure CORS configuration: `allow_origins=["*"]` combined with `allow_credentials=True`.
  - Missing environment variables cause immediate `ValidationError` crash on import.
  - Logging outputs unformatted text to standard output rather than structured JSON.
- **Recommended Future Action:** Refactor CORS for explicit origins; introduce environment validation defaults; transition logging to structured JSON.
- **Related Requirements:** REQ-BE-CORE, REQ-BE-SEC-01.

---

### MOD-BE-02: Authentication & Identity Management
- **Module Name:** Authentication API & Security Utilities
- **File Paths:**
  - `backend/app/api/auth.py`
  - `backend/app/api/deps.py`
  - `backend/app/core/security.py`
  - `backend/app/models/user.py`
- **Current Purpose:** User registration, password hashing, credential verification, and JWT bearer token issuance.
- **Existing Functionality:**
  - `POST /api/auth/signup`: Validates email uniqueness in MongoDB and stores bcrypt-hashed password.
  - `POST /api/auth/login`: Verifies credentials via OAuth2 password form data and issues a signed HS256 JWT access token (1440 min expiry). Rate-limited to 5 attempts/min.
  - `get_current_user`: FastAPI dependency decoding Bearer token and retrieving user record from MongoDB.
- **Dependencies:** `fastapi`, `bcrypt`, `python-jose`, `motor`, `pydantic`.
- **Tests:** None.
- **Known Issues:**
  - Custom JWT solution in MongoDB instead of approved Supabase Auth integration.
  - Deprecated `datetime.utcnow()` used for token expiration.
  - Pydantic v1 `__get_validators__` syntax in `PyObjectId`.
  - Missing refresh tokens, email verification, password reset, and role/workspace assignments.
- **Recommended Future Action:** Harmonize with Supabase Auth or implement standard refresh token rotation; transition to timezone-aware UTC datetime.
- **Related Requirements:** REQ-BE-AUTH-01, REQ-BE-AUTH-02.

---

### MOD-BE-03: Expense Management
- **Module Name:** Core Expense API
- **File Paths:**
  - `backend/app/api/expenses.py`
  - `backend/app/models/expense.py`
- **Current Purpose:** CRUD operations for user expenditures.
- **Existing Functionality:**
  - `POST /api/expenses/`: Creates expense, forcibly assigns AI category, and inserts document into MongoDB.
  - `GET /api/expenses/`: Returns latest 100 expenses sorted by date descending.
  - `DELETE /api/expenses/{expense_id}`: Permanently deletes expense document from MongoDB.
- **Dependencies:** `fastapi`, `motor`, `pydantic`, `bson`, `classifier.ai_categorizer`.
- **Tests:** None.
- **Known Issues:**
  - Floating-point `amount: float` introduces binary rounding inaccuracies.
  - Physical hard deletion via `delete_one`; zero audit trail or soft deletion.
  - Hardcoded limit of 100 expenses with no pagination query parameters.
  - Forcibly overrides user-selected category with ML prediction.
  - Lacks workspace isolation (`workspace_id`), multi-currency support, payment method tags, or transaction state.
- **Recommended Future Action:** Migrate to PostgreSQL relational schema with `Numeric(18, 4)`; implement soft deletes, pagination, and multi-workspace support.
- **Related Requirements:** REQ-FIN-EXP-01, REQ-FIN-DATA-01.

---

### MOD-BE-04: Budgeting & Forecasting
- **Module Name:** Budget Engine
- **File Paths:**
  - `backend/app/api/budget.py`
  - `backend/app/models/budget.py`
  - `backend/app/services/ml/forecaster.py`
- **Current Purpose:** Manages category spending limits, tracks current consumption, and forecasts future expenditures.
- **Existing Functionality:**
  - `POST /api/budget/`: Upserts monthly budget limit for a category.
  - `GET /api/budget/status`: Aggregates category spending against set limits.
  - `GET /api/budget/forecast`: Predicts next month's total spend using an ARIMA(1, 1, 1) model.
- **Dependencies:** `fastapi`, `motor`, `statsmodels`, `pandas`, `pydantic`.
- **Tests:** None.
- **Known Issues:**
  - **Critical Flaw:** `/api/budget/status` fails to filter expenses by current month, grouping all historical user expenses into current budget status.
  - Floating-point `limit: float`.
  - Synchronous execution of `ARIMA.fit()` on the FastAPI async event loop.
  - Fallback logic is a naive 30-day extrapolation of all-time daily average.
- **Recommended Future Action:** Fix month boundary aggregation; offload ARIMA forecasting to background tasks; enforce exact decimal limits.
- **Related Requirements:** REQ-FIN-BUD-01, REQ-ML-FC-01.

---

### MOD-BE-05: Financial Goals & Advisory
- **Module Name:** Milestones & Strategy Engine
- **File Paths:**
  - `backend/app/api/goals.py`
  - `backend/app/models/goal.py`
- **Current Purpose:** Tracks milestone savings targets and provides rule-based portfolio allocations.
- **Existing Functionality:**
  - `POST /api/goals/`: Creates a milestone target with target amount and current savings.
  - `GET /api/goals/`: Retrieves goals and extrapolates estimated completion dates.
  - `GET /api/goals/insights`: Generates educational investment profile advice based on monthly surplus.
  - `DELETE /api/goals/{goal_id}`: Hard deletes a goal document.
- **Dependencies:** `fastapi`, `motor`, `pydantic`.
- **Tests:** None.
- **Known Issues:**
  - Computes surplus and milestones against a hardcoded mock monthly income of ₹50,000.
  - No ledger reconciliation for goal deposits (no transfer from account to goal reserve).
  - Floating-point values throughout.
- **Recommended Future Action:** Connect goals directly to bank/account ledger reserves; replace mock income with actual cash flow analysis.
- **Related Requirements:** REQ-FIN-GOAL-01, REQ-AI-ADV-01.

---

### MOD-BE-06: Financial Analytics & Anomaly Detection
- **Module Name:** Analytics & Risk Engine
- **File Paths:**
  - `backend/app/api/analytics.py`
  - `backend/app/services/ml/anomaly.py`
- **Current Purpose:** Calculates monthly totals, category breakdown, daily trends, and flags outlier transactions.
- **Existing Functionality:**
  - MongoDB aggregation pipelines for monthly spend, category distribution, and daily spend trends.
  - `detect_anomalies`: Runs scikit-learn `IsolationForest` on up to 500 recent transactions.
- **Dependencies:** `fastapi`, `motor`, `pandas`, `scikit-learn`.
- **Tests:** None.
- **Known Issues:**
  - Trains an `IsolationForest` on the fly synchronously during HTTP requests.
  - Detects anomalies solely across `amount` and `day of month`, ignoring merchant historical deviations or variance by category.
- **Recommended Future Action:** Offload batch anomaly scoring to Celery background workers; utilize multi-dimensional feature vectors.
- **Related Requirements:** REQ-FIN-ANA-01, REQ-ML-ANOM-01.

---

### MOD-BE-07: Ingestion & AI Operations
- **Module Name:** ML Ops, Parser, Scanner & Chatbot
- **File Paths:**
  - `backend/app/api/ml_ops.py`
  - `backend/app/services/ml/parser.py`
  - `backend/app/services/ml/classifier.py`
  - `backend/app/services/ocr/scanner.py`
  - `backend/app/services/ml/chatbot.py`
  - `backend/app/core/supabase.py`
- **Current Purpose:** UPI SMS parsing, receipt OCR, automated categorization, and conversational AI.
- **Existing Functionality:**
  - `POST /api/ml/parse-sms`: Extracts amount, merchant, and category from Indian banking SMS text.
  - `POST /api/ml/scan-receipt`: Uses Tesseract OCR to extract totals from receipt images and uploads images to Supabase storage.
  - `POST /api/ml/chat`: Prompts Gemini with user spending context and returns conversational advice.
- **Dependencies:** `pytesseract`, `Pillow`, `google-generativeai`, `supabase`, `scikit-learn`, `joblib`.
- **Tests:** None.
- **Known Issues:**
  - Hardcoded Windows Tesseract path breaks Linux and containerized environments.
  - Memory exhaustion vulnerability on receipt file upload (`await file.read()`).
  - Deprecated `google.generativeai` SDK.
  - Chat prompt vulnerable to prompt injection via `user_query`.
  - Synchronous `joblib.load()` on every classifier prediction.
- **Recommended Future Action:** Migrate to `google-genai` SDK; use configurable Tesseract path with error degradation; introduce background OCR processing.
- **Related Requirements:** REQ-ING-SMS-01, REQ-ING-OCR-01, REQ-AI-LLM-01.

---

### MOD-BE-08: Financial Reporting & Statements
- **Module Name:** Statement Export Engine
- **File Paths:**
  - `backend/app/api/reports.py`
- **Current Purpose:** Generates downloadable Excel spreadsheets and PDF financial statements.
- **Existing Functionality:**
  - `GET /api/reports/excel`: Generates styled `.xlsx` file using openpyxl and pandas.
  - `GET /api/reports/pdf`: Generates formal PDF statement using ReportLab SimpleDocTemplate.
- **Dependencies:** `reportlab`, `pandas`, `openpyxl`.
- **Tests:** None.
- **Known Issues:**
  - CPU-intensive PDF rendering executed directly on async event loop.
  - Hardcoded transaction limit (100 in PDF, 1000 in Excel) with no date range filtering.
- **Recommended Future Action:** Implement date range filters and offload large exports to async task processing.
- **Related Requirements:** REQ-FIN-REP-01.

---

### MOD-BE-09: Unimplemented Backend Placeholders
- **Module Name:** Abandoned Backend Services
- **File Paths:**
  - `backend/app/services/recommendations.py` (0 bytes)
  - `backend/app/services/report_gen.py` (0 bytes)
- **Current Purpose:** Intended service modules that were left completely empty during initial prototype build.
- **Existing Functionality:** None.
- **Dependencies:** None.
- **Tests:** None.
- **Recommended Future Action:** Flesh out into domain service classes or clean up in subsequent service layer refactoring.

---

## 2. FRONTEND MODULES

### MOD-FE-01: Application Shell & Navigation
- **Module Name:** Root Layout & Routing Shell
- **File Paths:**
  - `frontend/src/main.jsx`
  - `frontend/src/App.jsx`
  - `frontend/src/index.css`
  - `frontend/index.html`
- **Current Purpose:** React root render, browser routing, navigation bar, and protected route wrapper.
- **Existing Functionality:**
  - Client-side route protection checking Zustand `isAuthenticated`.
  - Top navigation bar with Lucide icons for Analytics, Expenses, Budget, Milestones, and Reports.
  - Global floating AIChatbot component mount.
- **Dependencies:** `react`, `react-dom`, `react-router-dom`, `lucide-react`, `zustand`.
- **Tests:** None.
- **Known Issues:**
  - Written in JavaScript JSX instead of TypeScript (`.tsx`).
  - Auth protection relies solely on client-side localStorage token presence.
  - Lacks responsive drawer/sheet for mobile viewports.
- **Recommended Future Action:** Convert to TypeScript (`.tsx`); implement robust token verification gate.
- **Related Requirements:** REQ-FE-SHELL-01.

---

### MOD-FE-02: Authentication Page
- **Module Name:** Login & Registration View
- **File Paths:**
  - `frontend/src/pages/Auth.jsx`
  - `frontend/src/store/useAuthStore.js`
- **Current Purpose:** User sign-in and account registration.
- **Existing Functionality:**
  - Toggle between Login and Signup modes.
  - Submits credentials via Zustand `login` / `signup` actions.
- **Dependencies:** `react`, `react-router-dom`, `lucide-react`, `zustand`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - API endpoint path mismatch (`/auth/login` vs backend `/api/auth/login`).
  - Native browser `alert()` on account creation.
  - No client-side schema validation (no Zod/React Hook Form).
- **Recommended Future Action:** Align API URLs, add form validation with Zod, replace alerts with toast notifications.
- **Related Requirements:** REQ-FE-AUTH-01.

---

### MOD-FE-03: Dashboard & Analytics View
- **Module Name:** Financial Analytics Dashboard
- **File Paths:**
  - `frontend/src/pages/Dashboard.jsx`
- **Current Purpose:** Overview of monthly spend, burn rate, anomaly alerts, spending velocity chart, and category breakdown.
- **Existing Functionality:**
  - Fetches summary from `/api/analytics/summary`.
  - Recharts AreaChart for 30-day velocity; PieChart for portfolio breakdown.
  - Banner displaying flagged statistical outlier expenses.
- **Dependencies:** `react`, `recharts`, `lucide-react`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - Flashing full-screen loading state ("Initializing AI Analytics...").
  - Lack of skeleton loaders.
  - Over-prominent AI gimmick banners.
- **Recommended Future Action:** Redesign to clean fintech aesthetic; add skeleton states and actionable financial KPIs.
- **Related Requirements:** REQ-FE-DASH-01.

---

### MOD-FE-04: Expenses View & Ingestion
- **Module Name:** Expense Management & Ingestion UI
- **File Paths:**
  - `frontend/src/pages/Expenses.jsx`
  - `frontend/src/store/useExpenseStore.js`
- **Current Purpose:** Transaction listing, manual addition, UPI SMS parsing interface, and receipt OCR camera upload.
- **Existing Functionality:**
  - Interactive modal for pasting SMS texts and calling `/api/ml/parse-sms`.
  - File input for uploading receipts to `/api/ml/scan-receipt`.
  - Manual transaction form and transaction list with category tags and delete button.
- **Dependencies:** `react`, `lucide-react`, `zustand`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - Uses native `alert()` on OCR scan failure.
  - Hard deletion without confirmation dialog.
  - Does not support filters, search, or pagination.
- **Recommended Future Action:** Add confirmation dialogs, search/filter controls, and toast notifications.
- **Related Requirements:** REQ-FE-EXP-01, REQ-ING-SMS-01.

---

### MOD-FE-05: Budgeting & Goals Views
- **Module Name:** Budgeting & Milestone Pages
- **File Paths:**
  - `frontend/src/pages/Budget.jsx`
  - `frontend/src/pages/Goals.jsx`
- **Current Purpose:** Budget tracking progress bars, ARIMA spending prediction display, milestone goals, and savings velocity tracking.
- **Existing Functionality:**
  - Visual category progress bars with threshold color shifting (>90% red).
  - Milestone creation form with progress bars and predicted completion dates.
- **Dependencies:** `react`, `lucide-react`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - Direct display of flawed all-time budget calculation from backend.
  - Relies on backend mock income (₹50k) for goal timeline display.
- **Recommended Future Action:** Reconcile with updated backend data contracts.
- **Related Requirements:** REQ-FE-BUD-01, REQ-FE-GOAL-01.

---

### MOD-FE-06: Export Reports & Statements View
- **Module Name:** Statement Export UI
- **File Paths:**
  - `frontend/src/pages/Reports.jsx`
- **Current Purpose:** Triggers download of generated PDF and Excel statement files.
- **Existing Functionality:**
  - Axios blob stream retrieval and local object URL download triggering.
- **Dependencies:** `react`, `lucide-react`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - No date range or account selector for targeted statement generation.
- **Recommended Future Action:** Introduce date picker and format selection filters.
- **Related Requirements:** REQ-FE-REP-01.

---

### MOD-FE-07: Conversational AI Assistant
- **Module Name:** Arthsavora AI Chatbot Component
- **File Paths:**
  - `frontend/src/components/AIChatbot.jsx`
- **Current Purpose:** Floating chat widget providing contextual advice via Gemini.
- **Existing Functionality:**
  - Expandable bottom-right overlay.
  - Submits messages to `/api/ml/chat` and renders conversational bubble history.
- **Dependencies:** `react`, `lucide-react`, `axios`.
- **Tests:** None.
- **Known Issues:**
  - No streaming response support (full round-trip latency).
  - Unsanitized chat messages.
- **Recommended Future Action:** Implement streaming tokens and structured financial responses.
- **Related Requirements:** REQ-FE-CHAT-01, REQ-AI-LLM-01.

---

### MOD-FE-08: Unimplemented Frontend Placeholders
- **Module Name:** Abandoned Frontend Hooks & Utilities
- **File Paths:**
  - `frontend/src/hooks/useAuth.js` (0 bytes)
  - `frontend/src/hooks/useExpenses.js` (0 bytes)
  - `frontend/src/utils/currency.js` (0 bytes)
  - `frontend/src/utils/date.js` (0 bytes)
- **Current Purpose:** Empty placeholder files created during initial scaffolding.
- **Existing Functionality:** None.
- **Recommended Future Action:** Implement canonical currency formatting (`Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })`) and date utilities or delete in clean refactoring.
