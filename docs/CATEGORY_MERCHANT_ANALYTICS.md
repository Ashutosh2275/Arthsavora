# Arthsavora Category & Merchant Spending Analytics

## 1. Overview

Understanding where capital is deployed is central to spending awareness and financial health. The **Category & Merchant Spending Engine** ranks expenditure, computes percentage shares, detects average ticket sizes, and isolates unclassified spending.

---

## 2. Category Breakdown & Hierarchy Aggregation

### 2.1 Category Spending Query Flow
1. Filters on workspace, active status, target date window, and direction (`outflow`).
2. Joins `transactions` with `categories` on `transactions.category_id = categories.id`.
3. Performs a SQL `GROUP BY` on category identity, computing $\sum \text{amount\_paise}$ and $\text{COUNT}(id)$.
4. Dynamically calculates `percentage_of_total` against the overall period spend.
5. Limits output to top $N$ categories (default 10, configurable up to 50).

### 2.2 Uncategorized Transactions Handling
When transactions have `category_id IS NULL`, they are grouped into a synthetic item:
```json
{
  "category_id": null,
  "category_name": "Uncategorized",
  "category_slug": "uncategorized",
  "icon": "help-circle",
  "color": "#94a3b8",
  "is_system": false,
  "is_uncategorized": true,
  "total_amount_paise": 450000,
  "total_amount": "4500.00",
  "percentage_of_total": 5.63,
  "transaction_count": 3
}
```
This guarantees that unclassified spending is visually prominent and actionable, prompting users to categorize transactions without failing the visual chart or distorting the overall spend total.

---

## 3. Merchant Spending & Ticket Intelligence

The merchant spending breakdown ranks commercial payees by aggregate expenditure:
- **Merchant Identity:** Extracted from `COALESCE(NULLIF(TRIM(merchant_name), ''), 'Other / Unspecified')`.
- **Ranking Metric:** Sorted by $\sum \text{amount\_paise} \text{ DESC}$.
- **Average Ticket Size:** Computed server-side as:
  $$\text{Average Ticket} = \left\lfloor \frac{\text{Total Merchant Spend}}{\text{Transaction Count}} \right\rfloor$$
- **Recency:** Preserves `MAX(transaction_date)` to indicate the most recent date of engagement with the vendor.

---

## 4. UI Visualization Contract

In `apps/web/src/pages/Dashboard.tsx`:
- Category breakdown is rendered as an interactive Recharts Donut chart (`innerRadius=60`, `outerRadius=88`) with high-contrast color palette, custom currency tooltips, and legend.
- Merchant spending is displayed as an ordered ranking list detailing vendor name, transaction count, average ticket size, and percentage of overall spend.
