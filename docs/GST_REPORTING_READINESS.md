# ARTHSAVORA — GST REPORTING READINESS

## 1. Objective & Non-Filing Scope

The GST Reporting Readiness engine assists registered small businesses, consultants, and service firms in compiling outward taxable turnover and output tax liabilities from issued commercial invoices (`BusinessInvoice`).

> [!WARNING]
> **Non-Filing Scope Limitation:**  
> This module generates structured accounting summaries to assist your chartered accountant or GST practitioner in filing GSTR-1 and GSTR-3B. It is **NOT** a direct GST portal connector, GSP/ASP filing gateway, or e-invoicing/e-way bill generator.

---

## 2. Calculation Mechanics

### 2.1 Taxable Turnover & Tax Breakdown
For all invoices issued within the reporting period with status `issued` or `paid`:
$$\text{Total Taxable Turnover} = \sum \text{Invoice Subtotal}$$
$$\text{Total CGST} = \sum \text{Invoice CGST}$$
$$\text{Total SGST} = \sum \text{Invoice SGST}$$
$$\text{Total IGST} = \sum \text{Invoice IGST}$$
$$\text{Total Tax Liability} = \text{Total CGST} + \text{Total SGST} + \text{Total IGST}$$

### 2.2 Place of Supply & Tax Nature
- **Intra-State Supply (Supplier State = Customer State):**  
  $\text{CGST} + \text{SGST}$ applies (e.g. 9% CGST + 9% SGST for an 18% slab).
- **Inter-State Supply (Supplier State $\neq$ Customer State):**  
  $\text{IGST}$ applies in full (e.g. 18% IGST).

### 2.3 Tax Slabs & Rate Breakdown
The engine aggregates invoices into canonical GST rate buckets:
- `0%` (Exempt / Nil Rated)
- `5%`
- `12%`
- `18%` (Standard Services / IT Consulting)
- `28%`

### 2.4 B2B vs B2C Segmentation
- **B2B:** Client profile includes a verified 15-character GSTIN. Listed with invoice numbers, client GSTIN, and taxable amounts for GSTR-1 Table 4 preparation.
- **B2C:** Retail or unregistered client supplies summarized for GSTR-1 Table 7 preparation.
