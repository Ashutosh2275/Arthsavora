# Notification Event Catalog & Phrasing Standards

## 1. Catalog Overview

The Arthsavora notification system standardizes event generation across all financial sub-systems through [event_catalog.py](file:///d:/Arthsavora/backend/app/services/notification/event_catalog.py). Every domain event is mapped to a strictly typed `NotificationPayloadVO` with a deterministic deduplication key, appropriate severity, and standardized user messaging.

---

## 2. Event Taxonomy by Category

### 2.1 A. Transaction Notifications (`transaction`)
| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `transaction.recorded` | Authoritative journal entry posted | `INFO` | `Transaction Recorded: ₹X.XX` |
| `transaction.imported` | Statement batch imported | `INFO` | `Transactions Imported: N items` |
| `transaction.confirmed` | User confirms receipt/draft | `SUCCESS` | `Transaction Confirmed: ₹X.XX` |
| `transaction.reversed` | Compensating reversal journal posted | `WARNING` | `Transaction Reversed: ₹X.XX` |
| `transaction.review_required` | Uncategorized or flagged transaction | `WARNING` | `Review Required: ₹X.XX at Merchant` |

### 2.2 B. Budget Notifications (`budget`)
| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `budget.approaching` | Spending reaches 80% threshold | `INFO` | `Budget Alert: [Category] at 80%` |
| `budget.threshold_reached` | Spending reaches 90% threshold | `WARNING` | `Budget Alert: [Category] at 90%` |
| `budget.exceeded` | Spending exceeds 100% of limit | `CRITICAL` | `Budget Exceeded: [Category] at 105%` |
| `budget.category_overspending` | Spending velocity indicates breach | `WARNING` | `Rapid Spending Alert: [Category]` |

### 2.3 C. Goal Notifications (`goal`)
| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `goal.contribution` | Deposit made toward goal | `INFO` | `Contribution Recorded: ₹X.XX to [Goal]` |
| `goal.milestone` | Reached 25%, 50%, 75% target | `SUCCESS` | `Goal Milestone: [Goal] reached 50%` |
| `goal.nearing_target` | Approaching target end date | `INFO` | `Target Date Approaching: [Goal]` |
| `goal.completed` | 100% target achieved | `SUCCESS` | `Goal Completed: [Goal] Achieved!` |

### 2.4 D. Recurring Finance & Reminders (`recurring`)
> **Invariant**: A reminder communicates an expectation, never proof of money transfer.

| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `recurring.upcoming_payment` | Payment due in 7, 3, or 1 days | `INFO` | `Upcoming Payment: [Name] in N days` |
| `recurring.payment_due` | Due date is today | `WARNING` | `Payment Due Today: [Name] (₹X.XX)` |
| `recurring.payment_overdue` | Due date passed without match | `CRITICAL` | `Payment Overdue: [Name] (₹X.XX)` |
| `recurring.upcoming_salary` | Expected payroll/salary deposit | `SUCCESS` | `Expected Salary: [Name] on [Date]` |
| `recurring.subscription_renewal`| Subscription renewal expected | `INFO` | `Subscription Renewal: [Name]` |
| `recurring.trial_ending` | Free trial ending soon | `WARNING` | `Trial Ending: [Name] in 3 days` |
| `recurring.subscription_cancelled`| Cancellation recorded | `INFO` | `Subscription Cancelled: [Name]` |

### 2.5 E. Forecasting & Predictive Intelligence (`forecast`)
> **Invariant**: Forecast-based notifications must be explicitly prefixed with `[Estimate]` and clearly noted as informational estimates.

| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `forecast.budget_exhaustion` | Projected depletion date | `INFO` | `[Estimate] Projected Budget Exhaustion: [Cat]` |
| `forecast.cashflow_change` | Predicted cash flow contraction | `WARNING` | `[Estimate] Projected Cash Flow Change` |
| `forecast.low_balance` | Projected account balance dip | `WARNING` | `[Estimate] Projected Low Balance Warning` |

### 2.6 F. Financial Anomaly & Risk Intelligence (`anomaly`)
> **Invariant**: An anomaly is never labeled as confirmed fraud. Wording is neutral and non-alarmist.

| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `anomaly.unusual_transaction` | High value / burst / outlier | `WARNING` | `Unusual Activity Noted: ₹X.XX at [Merchant]` |
| `anomaly.spending_pattern` | Category spending surge | `WARNING` | `Unusual Spending Pattern: [Category]` |
| `anomaly.unexpected_recurring` | Recurring hike or cancelled active | `WARNING` | `Recurring Change Detected: [Merchant]` |
| `anomaly.balance_discrepancy` | Account balance mismatch | `CRITICAL` | `Balance Discrepancy Flagged: [Account]` |

### 2.7 G. Document & Receipt Processing (`document`)
| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `document.processed` | OCR scanning complete | `INFO` | `Receipt Ready for Review: [Merchant] (₹X.XX)` |
| `document.review_required` | Mathematical discrepancy > ₹1.00 | `WARNING` | `Receipt Math Discrepancy: [Filename]` |
| `document.failed` | Corrupted image or invalid PDF | `CRITICAL` | `Document Scan Failed: [Filename]` |
| `document.matched` | Match candidate found | `INFO` | `Receipt Matched to Existing Transaction` |

### 2.8 H. AI Assistant (`assistant`)
| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `assistant.task_completed` | Background analysis complete | `INFO` | `Assistant Task Completed: [Task]` |
| `assistant.action_completed` | Confirmed action executed | `SUCCESS` | `Assistant Action Completed: [Action]` |
| `assistant.action_attention` | Action draft expires / fails | `WARNING` | `Action Requires Attention: [Action]` |

### 2.9 I. Security & Authentication (`security`)
> **Invariant**: Security alerts must never expose authentication tokens, passwords, or full credentials.

| Event Type | Trigger Condition | Severity | Title Pattern |
|---|---|---|---|
| `security.new_login` | Login from new device/IP | `CRITICAL` | `Security Alert: New Sign-In Detected` |
| `security.password_changed` | Password updated | `CRITICAL` | `Security Alert: Password Updated` |
| `security.auth_event` | Suspicious login burst / lock | `CRITICAL` | `Important Account Security Notification` |

---

## 3. Related Documentation

- [Notification Architecture](file:///d:/Arthsavora/docs/NOTIFICATION_ARCHITECTURE.md)
- [Notification Deduplication](file:///d:/Arthsavora/docs/NOTIFICATION_DEDUPLICATION.md)
- [Notification Security & Privacy](file:///d:/Arthsavora/docs/NOTIFICATION_SECURITY.md)
