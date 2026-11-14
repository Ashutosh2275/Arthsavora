# Arthsavora — Subscription Management Architecture & Workflows

## 1. Scope & Objective

Subscriptions represent recurring contractual agreements for software, memberships, utilities, content services, or licenses. The Subscription Management module wraps underlying recurring definitions with subscription-specific attributes, including trial periods, cancellation deadlines, renewal terms, and cost normalization.

---

## 2. Core Data Model (`subscriptions`)

Each subscription record links 1:1 to a `RecurringDefinition` while capturing dedicated subscription intelligence:

| Column | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary key. |
| `workspace_id` | `UUID` | Multi-tenant tenant boundary. |
| `recurring_definition_id` | `UUID` | Reference to parent recurring definition. |
| `service_name` | `VARCHAR(255)` | Service or vendor brand name (e.g. AWS, Netflix, Spotify). |
| `plan_name` | `VARCHAR(100)` | Tier or license (e.g. "Family Premium", "Developer Pro"). |
| `billing_cycle` | `VARCHAR(30)` | `monthly`, `annual`, `quarterly`, `weekly`. |
| `billing_amount_paise` | `BIGINT` | Cost per billing cycle in integer minor units (`paise`). |
| `billing_amount` | `NUMERIC(18, 4)` | Major currency representation. |
| `currency` | `VARCHAR(3)` | ISO 4217 currency code (default: `INR`). |
| `is_trial` | `BOOLEAN` | Whether the subscription is currently in a free or discounted trial. |
| `trial_end_date` | `DATE` | Expiration date of the trial. |
| `renewal_date` | `DATE` | Next scheduled billing renewal date. |
| `cancellation_deadline` | `DATE` | Deadline to cancel to avoid the next billing charge. |
| `auto_renew` | `BOOLEAN` | Whether the provider automatically charges on renewal. |
| `status` | `VARCHAR(20)` | `active`, `paused`, `trialing`, `cancelled`, `expired`. |

---

## 3. Cost Normalization Engine

Subscriptions often have diverse billing frequencies (e.g. \$10/month vs \$100/year vs \$25/quarter). Comparing raw amounts distorts budget planning.

The cost normalization engine converts any cycle amount into canonical **monthly** and **annualized** minor unit costs:

$$\text{Monthly Cost} = \begin{cases}
\text{amount} \times 30.4375, & \text{daily} \\
\frac{\text{amount} \times 52}{12}, & \text{weekly} \\
\frac{\text{amount} \times 26}{12}, & \text{biweekly} \\
\frac{\text{amount}}{\text{interval}}, & \text{monthly} \\
\frac{\text{amount}}{3 \times \text{interval}}, & \text{quarterly} \\
\frac{\text{amount}}{6 \times \text{interval}}, & \text{semi\_annual} \\
\frac{\text{amount}}{12 \times \text{interval}}, & \text{annual}
\end{cases}$$

$$\text{Annual Cost} = \text{Monthly Cost} \times 12$$

All calculations are rounded deterministically to the nearest integer `paise`.

---

## 4. Trial & Renewal Tracking Workflows

1. **Trial Expiration Tracking**:
   - Subscriptions with `is_trial = true` display countdown badges in the UI.
   - If `current_date > trial_end_date`, status automatically updates from `trialing` to `active` upon billing or prompts for review.

2. **Cancellation Deadline Protection**:
   - The system alerts users 3 to 7 days before `cancellation_deadline` so unwanted subscriptions can be revoked before automatic renewal.
   - Cancellation notes, help desk URLs, and direct cancellation steps can be saved in `notes` or `metadata`.

3. **Safe Cancellation Protocol**:
   - Cancelling a subscription sets its status to `cancelled` and pauses the linked recurring definition.
   - Future occurrences scheduled beyond the cancellation date are automatically removed or marked `cancelled`.
   - Past matched occurrences and historical accounting transactions remain completely untouched.
