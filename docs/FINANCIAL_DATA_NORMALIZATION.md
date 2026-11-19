# ARTHSAVORA Financial Data Normalization

## 1. Overview

External financial institutions and Account Aggregators expose transaction narratives, balances, and account numbers in disparate, unstructured, and vendor-specific formats.

The ARTHSAVORA Normalization Pipeline transforms messy, heterogeneous provider payloads into uniform, strictly validated domain models adhering to core architectural invariants:
- **Exact Minor Units (Paise)**: Zero floating-point representation.
- **Canonical Direction**: Binary `inflow` vs. `outflow` classification.
- **Privacy Masking**: Truncation and hashing of account numbers.
- **Deterministic Deduplication**: Workspace-isolated idempotency keys.

---

## 2. Direction & Minor Unit Normalization

External banks often use opposing conventions: some report negative numbers for debits, others provide `"DR"` / `"CR"` flags, while credit card issuers treat charges as positive liabilities.

The pure function `normalize_transaction_direction` in `app/domain/financial_connection.py` establishes the standard:

```python
def normalize_transaction_direction(
    raw_direction: str,
    amount_paise: int,
) -> Tuple[str, int]:
    """
    Normalizes direction to 'inflow' or 'outflow' and guarantees positive minor units.
    """
    cleaned = (raw_direction or "").strip().lower()
    abs_paise = abs(amount_paise)

    if cleaned in ("cr", "credit", "inflow", "deposit", "refund"):
        return "inflow", abs_paise
    elif cleaned in ("dr", "debit", "outflow", "withdrawal", "payment", "charge"):
        return "outflow", abs_paise
    else:
        # Fallback to sign of original amount
        if amount_paise < 0:
            return "outflow", abs_paise
        return "inflow", abs_paise
```

---

## 3. Account Number Masking

To maintain PCI-DSS and RBI confidentiality standards, full account numbers and card primary account numbers (PAN) are never stored in plaintext within `external_account_references` or `accounts`.

```python
def mask_account_identifier(raw_identifier: Optional[str]) -> str:
    """
    Securely masks an account or card number, exposing only the last 4 digits.
    Example: '123456789012' -> '•••• 9012'
    """
    if not raw_identifier:
        return "•••• ••••"
    cleaned = re.sub(r"\s+", "", str(raw_identifier))
    if len(cleaned) <= 4:
        return f"•••• {cleaned}"
    last_four = cleaned[-4:]
    return f"•••• {last_four}"
```

---

## 4. Indian Payment Narrative Cleansing

Indian bank statements contain heavy metadata within transaction lines:
- **UPI**: `UPI/DR/312456789012/SWIGGY/HDFC/Pay/swiggy@icici`
- **IMPS**: `IMPS-312456789012-RAVI KUMAR-HDFC0001`
- **NEFT**: `NEFT-HDFCN12345678901-TATA POWER CO LTD`
- **POS / Card**: `POS 412345XXXXXX1234 STARBUCKS MUMBAI IN`

The normalization layer extracts:
1. **Clean Merchant Name**: Removes routing prefixes (`UPI/DR/`, `POS `, `IMPS-`) and isolates the counterparty identity.
2. **Reference Number**: Extracts the 12-digit UTR/RRN number for automated deduplication and payment matching.
3. **Channel Tag**: Annotates `source_provenance` with payment channel (`UPI`, `IMPS`, `NEFT`, `CARD`, `ATM`).

---

## 5. Deduplication & Idempotency Key Design

Every transaction imported from a financial connection receives an `external_transaction_id`:
- If the provider supplies a unique reference (e.g., ReBIT transaction ID or bank UTR), it is used directly.
- If the provider does not provide a reliable unique key, a deterministic SHA-256 fingerprint is constructed:
  $$\text{Key} = \text{SHA256}(\text{account\_id} \mathbin{\Vert} \text{date} \mathbin{\Vert} \text{amount\_paise} \mathbin{\Vert} \text{direction} \mathbin{\Vert} \text{reference\_number})$$

Deduplication checks are scoped to the active workspace to prevent cross-tenant collision while guaranteeing zero double-counting within the user's accounts.
