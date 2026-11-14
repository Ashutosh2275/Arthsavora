# Arthsavora — Budget & Financial Goals API Reference

## 1. Overview & Authentication

All Budget and Financial Goal endpoints are secured under API version 1 (`/api/v1`). Every request must include:
- `Authorization: Bearer <access_token>`
- A valid workspace context passed either via the path parameter `/workspaces/{workspace_id}` or via header `x-workspace-id`.

### 1.1 Standard Response Envelope
Successful responses return HTTP `200 OK` or `201 Created` with the standard payload format:
```json
{
  "status": "success",
  "data": { ... },
  "error": null,
  "timestamp": "2026-11-14T08:00:00Z"
}
```

### 1.2 Permissions Matrix

| Endpoint Group | Read Permission | Write Permission |
|---|---|---|
| Budgets & Allocations | `VIEW_BUDGETS` | `MANAGE_BUDGETS` |
| Financial Goals & Ledger | `VIEW_GOALS` | `MANAGE_GOALS` |

---

## 2. Budget Endpoints

### 2.1 List Budgets
- **`GET /api/v1/workspaces/{workspace_id}/budgets`**
- **Permission**: `VIEW_BUDGETS`
- **Query Parameters**:
  - `status` (*optional*, `active` | `archived` | `draft` | `closed`)
  - `page` (*optional*, integer, default `1`)
  - `page_size` (*optional*, integer, default `20`)
- **Response**: List of `BudgetSummaryResponse` objects.

### 2.2 Create Budget
- **`POST /api/v1/workspaces/{workspace_id}/budgets`**
- **Permission**: `MANAGE_BUDGETS`
- **Request Body**:
  ```json
  {
    "name": "November 2026 Household Budget",
    "budget_type": "monthly",
    "recurrence_interval": "monthly",
    "start_date": "2026-11-01",
    "end_date": "2026-11-30",
    "currency": "INR",
    "total_limit_paise": 15000000,
    "warning_threshold_percentage": 80,
    "notes": "Regular monthly family budget",
    "allocations": [
      {
        "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "allocated_amount_paise": 5000000,
        "warning_threshold_percentage": 75,
        "notes": "Groceries allocation"
      }
    ]
  }
  ```
- **Response**: `BudgetDetailResponse` with status `201 Created`.

### 2.3 Get Budget Detail
- **`GET /api/v1/workspaces/{workspace_id}/budgets/{budget_id}`**
- **Permission**: `VIEW_BUDGETS`
- **Response**: `BudgetDetailResponse` including associated category allocations.

### 2.4 Update Budget Parameters
- **`PATCH /api/v1/workspaces/{workspace_id}/budgets/{budget_id}`**
- **Permission**: `MANAGE_BUDGETS`
- **Request Body**:
  ```json
  {
    "name": "November 2026 Household Budget (Revised)",
    "total_limit_paise": 16000000,
    "warning_threshold_percentage": 85,
    "reason": "Increased fuel costs for festival commute"
  }
  ```
- **Notes**: Updates to limits automatically write an immutable audit record to `budget_revisions`.

### 2.5 Archive/Delete Budget
- **`DELETE /api/v1/workspaces/{workspace_id}/budgets/{budget_id}`**
- **Permission**: `MANAGE_BUDGETS`
- **Response**: `200 OK` confirming archiving or soft deletion.

### 2.6 Evaluate Budget Progress & Run-Rate Projections
- **`GET /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/progress`**
- **Permission**: `VIEW_BUDGETS`
- **Response Body**:
  ```json
  {
    "budget_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "November 2026 Household Budget",
    "currency": "INR",
    "total_limit_paise": 15000000,
    "actual_spent_paise": 4500000,
    "remaining_paise": 10500000,
    "utilization_percentage": 30.0,
    "warning_state": "normal",
    "days_elapsed": 14,
    "days_remaining": 16,
    "total_days": 30,
    "linear_projection": {
      "average_daily_spend_paise": 321428,
      "projected_total_spend_paise": 9642840,
      "projected_overspend_paise": 0,
      "will_exceed_budget": false,
      "methodology": "linear_run_rate"
    },
    "allocations": [
      {
        "allocation_id": "7ca85f64-5717-4562-b3fc-2c963f66afa7",
        "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "category_name": "Groceries",
        "allocated_amount_paise": 5000000,
        "actual_spent_paise": 2000000,
        "remaining_paise": 3000000,
        "utilization_percentage": 40.0,
        "warning_state": "normal"
      }
    ]
  }
  ```

### 2.7 List Budget Revisions
- **`GET /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/revisions`**
- **Permission**: `VIEW_BUDGETS`
- **Response**: Array of `BudgetRevisionResponse` chronologically sorted descending.

### 2.8 List Dispatched Alerts
- **`GET /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/alerts`**
- **Permission**: `VIEW_BUDGETS`
- **Response**: Array of `BudgetAlertResponse`.

### 2.9 Rollover Budget to Next Period
- **`POST /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/rollover`**
- **Permission**: `MANAGE_BUDGETS`
- **Request Body**:
  ```json
  {
    "new_start_date": "2026-12-01",
    "new_end_date": "2026-12-31",
    "copy_allocations": true,
    "rollover_unspent": false
  }
  ```
- **Response**: Newly created `BudgetDetailResponse` with status `201 Created`.

---

## 3. Allocation Sub-Endpoints

- **`POST /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/allocations`**: Add category allocation.
- **`PATCH /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/allocations/{allocation_id}`**: Update category limit or warning threshold.
- **`DELETE /api/v1/workspaces/{workspace_id}/budgets/{budget_id}/allocations/{allocation_id}`**: Remove category allocation from budget.

---

## 4. Financial Goal Endpoints

### 4.1 List Financial Goals
- **`GET /api/v1/workspaces/{workspace_id}/goals`**
- **Permission**: `VIEW_GOALS`
- **Query Parameters**:
  - `status` (*optional*, `active` | `completed` | `paused` | `archived`)
  - `page`, `page_size`

### 4.2 Create Financial Goal
- **`POST /api/v1/workspaces/{workspace_id}/goals`**
- **Permission**: `MANAGE_GOALS`
- **Request Body**:
  ```json
  {
    "name": "Emergency Reserve Fund",
    "goal_type": "emergency_fund",
    "priority": "high",
    "target_amount_paise": 30000000,
    "initial_amount_paise": 5000000,
    "currency": "INR",
    "start_date": "2026-11-01",
    "target_date": "2027-10-31",
    "notes": "6 months of liquid living reserves"
  }
  ```

### 4.3 Get Goal Details
- **`GET /api/v1/workspaces/{workspace_id}/goals/{goal_id}`**
- **Permission**: `VIEW_GOALS`

### 4.4 Update Goal Parameters
- **`PATCH /api/v1/workspaces/{workspace_id}/goals/{goal_id}`**
- **Permission**: `MANAGE_GOALS`

### 4.5 Archive Goal
- **`DELETE /api/v1/workspaces/{workspace_id}/goals/{goal_id}`**
- **Permission**: `MANAGE_GOALS`

### 4.6 Record Contribution
- **`POST /api/v1/workspaces/{workspace_id}/goals/{goal_id}/contributions`**
- **Permission**: `MANAGE_GOALS`
- **Request Body**:
  ```json
  {
    "amount_paise": 2500000,
    "notes": "Transferred from monthly savings account",
    "transaction_id": null
  }
  ```
- **Response**: `GoalActivityResponse` recording the contribution and new resulting balance.

### 4.7 Record Withdrawal
- **`POST /api/v1/workspaces/{workspace_id}/goals/{goal_id}/withdrawals`**
- **Permission**: `MANAGE_GOALS`
- **Request Body**:
  ```json
  {
    "amount_paise": 1000000,
    "notes": "Emergency dental procedure"
  }
  ```
- **Error**: Rejects with `400 Bad Request` if requested withdrawal exceeds available balance.

### 4.8 Evaluate Goal Progress & Required Monthly Pacing
- **`GET /api/v1/workspaces/{workspace_id}/goals/{goal_id}/progress`**
- **Permission**: `VIEW_GOALS`
- **Response Body**:
  ```json
  {
    "goal_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Emergency Reserve Fund",
    "currency": "INR",
    "target_amount_paise": 30000000,
    "current_amount_paise": 7500000,
    "remaining_paise": 22500000,
    "completion_percentage": 25.0,
    "status": "active",
    "days_remaining": 351,
    "required_monthly_savings_paise": 1951347,
    "is_on_track": true
  }
  ```

### 4.9 Paginated Activity Ledger
- **`GET /api/v1/workspaces/{workspace_id}/goals/{goal_id}/activity`**
- **Permission**: `VIEW_GOALS`
- **Query Parameters**: `page` (default `1`), `page_size` (default `20`)
- **Response**: Paginated array of immutable `GoalActivityResponse` entries.

---

## 5. File References

- Route Declarations: [budget_routes.py](file:///d:/Arthsavora/backend/app/api/v1/budget_routes.py) & [goal_routes.py](file:///d:/Arthsavora/backend/app/api/v1/goal_routes.py)
- Pydantic Schemas: [budget_schema.py](file:///d:/Arthsavora/backend/app/schemas/budget_schema.py) & [goal_schema.py](file:///d:/Arthsavora/backend/app/schemas/goal_schema.py)
- OpenAPI Specification: [openapi.json](file:///d:/Arthsavora/docs/openapi.json)
