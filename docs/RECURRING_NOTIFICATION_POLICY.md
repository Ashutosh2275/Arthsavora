# Arthsavora — Recurring Reminders & Notification Policy

## 1. Scope & Objective

This document specifies the notification policy for upcoming recurring commitments, subscription renewal deadlines, trial expirations, and overdue occurrences. Timely alerts prevent unexpected account overdrafts, penalty fees, and unwanted subscription renewals.

---

## 2. Notification Triggers & Lead Times

| Event Type | Default Lead Time | Secondary Notice | Channel Priority |
|---|---|---|---|
| **Upcoming Bill / Outflow** | 3 days prior | Day of due date | In-App Dashboard, Push / Email |
| **Subscription Renewal** | 7 days prior | 1 day prior | In-App Dashboard, Push / Email |
| **Trial Ending** | 5 days prior | 1 day prior | In-App Dashboard Banner, Push / Email |
| **Cancellation Deadline** | 3 days prior | Morning of deadline | Urgent In-App Banner, Email |
| **Overdue Occurrence** | 2 days post-due | 5 days post-due | In-App Warning, Digest Summary |
| **Expected Inflow / Salary** | 1 day prior | Day of arrival | In-App Dashboard |

---

## 3. Idempotency & Anti-Spam Governance

1. **Unique Reminder Tracking**:
   - The table `recurring_reminders` tracks every generated notification with `(recurring_definition_id, occurrence_id, days_before)`.
   - The system never sends duplicate reminders for the same occurrence on the same day.

2. **User Preferences & Quiet Hours**:
   - Users can customize reminder lead times per definition (e.g. 1 day, 3 days, 7 days, 14 days).
   - High-priority alerts respect user quiet hours (10:00 PM to 8:00 AM local time).

3. **Automatic Dismissal**:
   - When an occurrence is matched or confirmed, any pending reminders for that specific occurrence are automatically marked `dismissed` to prevent phantom alerts.
