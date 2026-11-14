# ARTHSAVORA — Financial Intent Understanding & Natural Language Processing

## 1. Overview

Natural language processing in Arthsavora converts unstructured, conversational user queries into deterministic, strongly-typed domain representations. This ensures that ambiguities in human phrasing do not compromise institutional financial accounting.

The intent understanding engine lives in `backend/app/domain/assistant.py` as a pure, zero-dependency functional layer.

---

## 2. Intent Taxonomy (`FinancialIntentEnum`)

| Intent Code | Value | Description | Typical Query Examples |
| :--- | :--- | :--- | :--- |
| `OVERVIEW` | `financial_overview` | High-level financial KPIs | "Show my financial overview", "How am I doing financially?" |
| `INCOME` | `income_summary` | Aggregate revenue & earnings | "What was my income this month?", "How much did I earn?" |
| `EXPENSE` | `expense_summary` | Total spending & outflow | "How much did I spend this month?", "Where did my money go?" |
| `CASH_FLOW` | `cash_flow_analysis` | Net cash flow & net savings | "What is my cash flow?", "Show inflow vs outflow" |
| `CATEGORY` | `category_analysis` | Spending grouped by category | "How much did I spend on Food?", "Groceries breakdown" |
| `MERCHANT` | `merchant_analysis` | Spending at specific vendors | "How much did I spend at Swiggy?", "Payments at Amazon" |
| `TRANSACTIONS` | `transaction_search` | Filtered transaction listings | "Show my transactions above ₹5,000", "Recent payments" |
| `ACCOUNT` | `account_balances` | Liquid & liability balances | "What is my bank balance?", "Account balances" |
| `BUDGET` | `budget_status` | Category budget consumption | "Am I likely to exceed my budget?", "Remaining budget for Dining" |
| `GOAL` | `goal_progress` | Savings target completion | "How much have I saved toward my goal?", "Car savings progress" |
| `RECURRING` | `recurring_commitments` | Bills & commitments due | "What payments are due this week?", "Upcoming EMI commitments" |
| `SUBSCRIPTIONS` | `subscription_summary` | Active recurring services | "Which subscriptions are active?", "How much do I pay for Netflix?" |
| `FORECAST` | `forecast_interpretation`| Cash-flow projections | "What is my projected balance next month?", "30-day cash forecast" |
| `ANOMALY` | `anomaly_explanation` | Unusual charge review | "Explain this unusual transaction", "Why was this flagged?" |
| `ACTION_BUDGET` | `action_create_budget` | Stage budget proposal draft | "Create a monthly budget for Food of ₹15,000" |
| `ACTION_GOAL` | `action_create_goal` | Stage savings goal draft | "Set a savings goal of 5 lakh for New Car" |
| `ACTION_RECURRING` | `action_create_recurring` | Stage recurring draft | "Set recurring rent payment of ₹25,000" |
| `EDUCATION` | `financial_education` | General financial concepts | "What is an emergency fund?", "Explain 50-30-20 rule" |
| `HELP` | `general_help` | System capabilities & usage | "What can you do?", "Help with commands" |

---

## 3. Natural Language Date Range Parsing (`DateRangeVO`)

Financial questions frequently utilize relative temporal concepts ("this month", "last 30 days", "yesterday"). The `parse_financial_date_range(query, ref_date)` parser converts these into exact `date` boundaries:

- **"today"**: `start_date = today, end_date = today`
- **"yesterday"**: `start_date = today - 1, end_date = today - 1`
- **"this week"**: Monday to Sunday of the active calendar week.
- **"last week"**: Monday to Sunday of the preceding calendar week.
- **"this month"**: First day to last day of current calendar month.
- **"last month"**: First day to last day of previous calendar month.
- **"last N days"**: Rolling `N` days prior to today.
- **"this year" / "last year"**: Jan 1 to Dec 31 of respective years.

---

## 4. Monetary & Currency Parsing

`parse_currency_and_amount(text)` extracts currency codes and converts all monetary values into **integer minor units (paise)** to prevent floating-point inaccuracies:

- **Rupee symbols & text**: Recognizes `₹`, `Rs`, `Rs.`, `INR`, `rupees`, `paise`.
- **Foreign currencies**: Recognizes `$`, `USD`, `€`, `EUR`, `£`, `GBP`.
- **Multipliers**:
  - `k`: Multiplies by 1,000 (e.g., `50k` -> `5,000,000` paise).
  - `lakh` / `lac`: Multiplies by 100,000 (e.g., `2.5 lakh` -> `25,000,000` paise).
  - `crore` / `cr`: Multiplies by 10,000,000 (e.g., `1 crore` -> `1,000,000,000` paise).
