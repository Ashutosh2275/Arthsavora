# ARTHSAVORA — Financial Tool Registry & Tool Specifications

## 1. Overview

The **Financial Tool Registry** (`backend/app/services/assistant/tool_registry.py`) defines the complete, authoritative catalog of capabilities exposed to the AI Assistant. Each tool declaration specifies strict parameter types, JSON schemas, required RBAC permissions, and data sensitivity classifications.

Tools are split into two distinct categories:
1. **14 Read-Only Financial Query Tools**: Retrieve verified aggregations, trends, and records.
2. **4 Action Proposal Draft Tools**: Propose reversible state modifications requiring explicit human confirmation.

---

## 2. Complete Tool Catalog

| Tool Name | Type | Required Permission | Sensitivity | Description |
| :--- | :--- | :--- | :--- | :--- |
| `get_financial_overview` | Read-only | `analytics:view` | Restricted | Inflow, outflow, net savings, transaction volume KPIs |
| `get_income_summary` | Read-only | `analytics:view` | Restricted | Aggregate earnings grouped by category or date |
| `get_expense_summary` | Read-only | `analytics:view` | Restricted | Aggregate expenses grouped by category or period |
| `get_cash_flow` | Read-only | `analytics:view` | Restricted | Net cash flow trends across monthly or daily intervals |
| `get_category_spending` | Read-only | `analytics:view` | Restricted | Breakdown of expenditures for specific categories |
| `get_merchant_spending` | Read-only | `analytics:view` | Restricted | Top merchants and expenditure distribution |
| `get_account_balances` | Read-only | `accounts:view` | Confidential | Balances for liquid, savings, and credit accounts |
| `search_transactions` | Read-only | `transactions:view` | Confidential | Bounded list of transactions matching criteria |
| `get_budget_status` | Read-only | `budgets:view` | Internal | Budget limits, spent amounts, and utilization ratios |
| `get_goal_progress` | Read-only | `goals:view` | Internal | Progress toward active savings goals |
| `get_upcoming_commitments`| Read-only | `recurring:view` | Restricted | Recurring payments and bills due in upcoming days |
| `get_subscription_summary`| Read-only | `subscriptions:view` | Restricted | Active subscriptions, billing cadences, and annual cost |
| `get_forecast` | Read-only | `forecasts:view` | Restricted | Cash-flow predictions and projected account balances |
| `get_anomaly_details` | Read-only | `anomalies:view` | Confidential | Anomaly risk scores, triggered rules, and explanations |
| `create_budget_draft` | Action Proposal | `budgets:manage` | Internal | Stages a proposal to create a category/monthly budget |
| `create_goal_draft` | Action Proposal | `goals:manage` | Internal | Stages a proposal to create a savings goal |
| `create_recurring_draft` | Action Proposal | `recurring:manage` | Internal | Stages a proposal to schedule a recurring commitment |
| `prepare_transaction_filter`| Action Proposal | `transactions:view` | Public | Generates UI deep-link filters for transaction search |

---

## 3. Parameter Schema Specification Example

### `get_category_spending`
```json
{
  "type": "object",
  "properties": {
    "category_name": {
      "type": "string",
      "description": "Optional category name filter (e.g. Food, Utilities, Transport)"
    },
    "start_date": {
      "type": "string",
      "description": "ISO start date YYYY-MM-DD"
    },
    "end_date": {
      "type": "string",
      "description": "ISO end date YYYY-MM-DD"
    },
    "currency": {
      "type": "string",
      "default": "INR"
    }
  }
}
```

### `create_budget_draft`
```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string", "description": "Budget name" },
    "period": { "type": "string", "enum": ["monthly", "quarterly", "annual"], "default": "monthly" },
    "limit_paise": { "type": "integer", "description": "Spending limit in minor currency units (paise)" },
    "category_name": { "type": "string", "description": "Target category name" },
    "currency": { "type": "string", "default": "INR" }
  },
  "required": ["name", "limit_paise"]
}
```

---

## 4. Permission Filtering

The assistant prompt context only advertises tools that the requesting user's active workspace role has explicit permission to execute:

```python
available_tools = list_available_tools_for_user(user_permissions)
```

If an unauthorized tool call is attempted by an LLM hallucination, `ToolExecutor` immediately rejects execution with `Permission denied: Missing required permission`.
