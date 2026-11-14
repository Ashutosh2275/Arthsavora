# Arthsavora Financial Analytics API Reference

All routes are authenticated via Bearer JWT and strictly partitioned by workspace tenancy (`X-Workspace-ID` or URI parameter `/workspaces/{workspace_id}/analytics/...`).

---

## 1. Financial Overview
`GET /api/v1/workspaces/{workspace_id}/analytics/overview`  
*(Alias: `/api/v1/analytics/overview`)*

Computes high-level financial KPIs, net cash flow, savings rate, and data quality indicators for the requested date window.

### Query Parameters
- `start_date` *(optional, string YYYY-MM-DD)*: Start date. Defaults to 1st of current month.
- `end_date` *(optional, string YYYY-MM-DD)*: End date. Defaults to current date.
- `currency` *(optional, string, default: "INR")*: 3-letter ISO currency code.
- `account_id` *(optional, UUID)*: Optional single-account filter.

### Required Permission
`Permission.VIEW_ANALYTICS` (`analytics:view`)

### Response Envelope (`200 OK`)
```json
{
  "success": true,
  "data": {
    "workspace_id": "78204b49-b0c3-4ce4-82a9-c5c83aa25c64",
    "currency": "INR",
    "start_date": "2026-02-01",
    "end_date": "2026-02-28",
    "total_income_paise": 10000000,
    "total_income": "100000.00",
    "gross_expenses_paise": 2300000,
    "refunds_paise": 100000,
    "total_expenses_paise": 2200000,
    "total_expenses": "22000.00",
    "net_cash_flow_paise": 7800000,
    "net_cash_flow": "78000.00",
    "savings_paise": 7800000,
    "savings": "78000.00",
    "savings_rate_percentage": 78.0,
    "transaction_count": 6,
    "average_daily_spend_paise": 78571,
    "average_daily_spend": "785.71",
    "days_in_period": 28,
    "data_quality": {
      "uncategorized_count": 1,
      "uncategorized_amount_paise": 300000,
      "uncategorized_amount": "3000.00",
      "excluded_transfers_count": 2,
      "excluded_transfers_amount_paise": 3000000,
      "excluded_transfers_amount": "30000.00",
      "excluded_pending_count": 1,
      "excluded_pending_amount_paise": 250000,
      "excluded_pending_amount": "2500.00"
    }
  }
}
```

---

## 2. Cash Flow Trends
`GET /api/v1/workspaces/{workspace_id}/analytics/cash-flow`

Retrieves bucketed cash flow series (income, expense, net flow, cumulative flow).

### Query Parameters
- `start_date` *(optional, string YYYY-MM-DD)*
- `end_date` *(optional, string YYYY-MM-DD)*
- `grouping` *(optional, string, default: "month")*: `'day'`, `'week'`, `'month'`, `'quarter'`, `'financial_year'`
- `currency` *(optional, string, default: "INR")*
- `account_id` *(optional, UUID)*

### Response Envelope (`200 OK`)
```json
{
  "success": true,
  "data": {
    "currency": "INR",
    "grouping": "month",
    "start_date": "2026-02-01",
    "end_date": "2026-02-28",
    "trends": [
      {
        "period_start": "2026-02-01",
        "period_label": "Feb 2026",
        "income_paise": 10000000,
        "income": "100000.00",
        "expenses_paise": 2200000,
        "expenses": "22000.00",
        "net_cash_flow_paise": 7800000,
        "net_cash_flow": "78000.00",
        "cumulative_cash_flow_paise": 7800000,
        "cumulative_cash_flow": "78000.00",
        "transaction_count": 6
      }
    ]
  }
}
```

---

## 3. Category Spending Breakdown
`GET /api/v1/workspaces/{workspace_id}/analytics/categories`

Returns categorized spending and percentage shares.

### Query Parameters
- `direction` *(optional, default: "outflow")*: `'outflow'` or `'inflow'`
- `limit` *(optional, default: 10, max: 50)*
- `start_date`, `end_date`, `currency`, `account_id`

---

## 4. Merchant Spending Breakdown
`GET /api/v1/workspaces/{workspace_id}/analytics/merchants`

Ranks top commercial merchants by total expenditure, volume, and average ticket size.

### Query Parameters
- `limit` *(optional, default: 10, max: 50)*
- `start_date`, `end_date`, `currency`, `account_id`

---

## 5. Account Balances & Net Worth
`GET /api/v1/workspaces/{workspace_id}/analytics/net-worth`

Derives real-time balance sheet: Total Assets, Total Liabilities, and Net Worth.

### Query Parameters
- `currency` *(optional, default: "INR")*

---

## 6. Period Performance Comparison
`GET /api/v1/workspaces/{workspace_id}/analytics/comparison`

Compares two date intervals with monetary deltas, percentage change, and directional sentiments.

### Query Parameters
- `current_start` *(required, string YYYY-MM-DD)*
- `current_end` *(required, string YYYY-MM-DD)*
- `previous_start` *(optional, string YYYY-MM-DD)*
- `previous_end` *(optional, string YYYY-MM-DD)*
- `currency`, `account_id`

---

## 7. Controlled CSV Export
`GET /api/v1/workspaces/{workspace_id}/analytics/export`

Streams sanitized CSV export with formula injection protection.

### Query Parameters
- `report_type` *(required)*: `'overview'`, `'cash_flow'`, `'categories'`, `'merchants'`, `'net_worth'`
- `start_date`, `end_date`, `currency`, `account_id`

### Required Permission
`Permission.EXPORT_ANALYTICS` (`analytics:export`)

### Response Headers
```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="arthsavora_overview_2026-02-01_2026-02-28.csv"
Cache-Control: no-cache, no-store, must-revalidate
```
