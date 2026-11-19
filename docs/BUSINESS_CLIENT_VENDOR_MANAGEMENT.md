# Business Client and Vendor Management Architecture

## 1. Client Management (`BusinessClient`)

Clients represent corporate entities, individuals, or institutions receiving commercial goods and services from the business.

### Key Fields & Contracts:
- `name`: Clean corporate or legal trade name.
- `client_type`: `business`, `individual`, or `government`.
- `email` & `phone`: Primary billing contact channels.
- `billing_address`: Structured JSON containing street address, city, state, postal code, and country.
- `gstin`: Validated 15-character statutory GST identification.
- `pan`: Validated 10-character Indian income tax identifier.
- `payment_terms_days`: Default credit period (e.g. 15, 30, 45, or 60 days).
- `currency`: Default billing currency (`INR`).

### Duplicate Name Detection:
To avoid fragmented ledger postings and split receivables, client name creation performs case-insensitive whitespace-normalized uniqueness checks within the active workspace. Attempting to add an existing name raises `ConflictException`.

---

## 2. Vendor Management (`BusinessVendor`)

Vendors represent contractors, SaaS providers, utilities, landlords, and suppliers providing services or goods to the business.

### Key Fields & Contracts:
- `name`: Supplier trade name.
- `vendor_type`: `contractor`, `service_provider`, `supplier`, `utility`, `landlord`.
- `email` & `phone`: Accounts payable contact info.
- `billing_details`: Bank transfer details, IFSC code, or UPI ID for disbursals.
- `gstin` & `pan`: Vendor statutory tax numbers for input tax credit (ITC) reconciliation.
- `payment_terms_days`: Negotiated vendor credit terms.

### Operational Controls:
- Active vs. Inactive status to archive deprecated suppliers without breaking historical payables.
- Automatic linkage to Accounts Payable records (`BusinessPayable`).
