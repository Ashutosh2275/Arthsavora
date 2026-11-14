"""
Arthsavora Document Field Extractor & Entity Normalizer
Parses raw OCR text into structured financial value objects, extracts Indian tax identifiers,
reconciles arithmetic balances, and assigns granular field-level confidence scores.
"""

from decimal import Decimal
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.domain.document import (
    DocumentLineItemVO,
    PaymentMethod,
    StructuredReceiptDataVO,
    TaxBreakdownVO,
    ValidationStatus,
    is_valid_gstin,
    parse_indian_date,
    parse_monetary_amount,
    validate_receipt_math,
)

logger = logging.getLogger(__name__)

# Common non-merchant header phrases to discard when scanning for merchant name
GENERIC_HEADER_PATTERNS = [
    r"^tax invoice",
    r"^cash memo",
    r"^bill of supply",
    r"^retail invoice",
    r"^receipt",
    r"^original for recipient",
    r"^duplicate for transporter",
    r"^order summary",
    r"^customer copy",
    r"^invoice",
]


class ReceiptFieldExtractor:
    """Intelligent rule-based parser and entity extractor for Indian receipts and invoices."""

    @classmethod
    def extract_structured_data(
        cls,
        raw_text: str,
    ) -> Tuple[StructuredReceiptDataVO, Dict[str, float], Decimal, ValidationStatus, List[str]]:
        """
        Parses raw text and returns:
        (structured_receipt_vo, field_confidences, overall_confidence, validation_status, validation_warnings)
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        field_confidences: Dict[str, float] = {}

        # 1. Extract GSTIN
        gstin, gstin_conf = cls._extract_gstin(raw_text, lines)
        if gstin:
            field_confidences["gstin"] = gstin_conf

        # 2. Extract Merchant Name
        merchant, merchant_conf = cls._extract_merchant_name(lines, gstin)
        field_confidences["merchant_name"] = merchant_conf

        # 3. Extract Receipt Date
        receipt_date, date_conf = cls._extract_date(raw_text, lines)
        field_confidences["receipt_date"] = date_conf

        # 4. Extract Invoice / Bill Number
        invoice_number, inv_conf = cls._extract_invoice_number(raw_text, lines)
        field_confidences["invoice_number"] = inv_conf

        # 5. Extract Monetary Values (Total, Subtotal, Taxes, Discount)
        total_dec, total_paise, total_conf = cls._extract_total_amount(raw_text, lines)
        field_confidences["total_amount"] = total_conf

        subtotal_dec, subtotal_paise, sub_conf = cls._extract_subtotal(raw_text, lines)
        field_confidences["subtotal"] = sub_conf

        tax_breakdown, tax_conf = cls._extract_tax_breakdown(raw_text, lines, gstin)
        field_confidences["taxes"] = tax_conf

        discount_dec, discount_paise, disc_conf = cls._extract_discount(raw_text, lines)
        field_confidences["discount"] = disc_conf

        # 6. Extract Payment Mode & Reference
        payment_method, payment_ref, pay_conf = cls._extract_payment_details(raw_text, lines)
        field_confidences["payment_method"] = pay_conf

        # 7. Extract Line Items
        line_items, items_conf = cls._extract_line_items(lines)
        field_confidences["line_items"] = items_conf

        # Fallback total from line items or subtotal if total wasn't found
        if total_paise <= 0 and subtotal_paise > 0:
            total_paise = subtotal_paise + tax_breakdown.total_tax_paise - discount_paise
            total_dec = Decimal(total_paise) / Decimal(100)
            total_conf = max(0.40, sub_conf * 0.8)
            field_confidences["total_amount"] = total_conf

        # 8. Perform Arithmetic Validation
        val_status, val_warnings = validate_receipt_math(
            subtotal_paise=subtotal_paise,
            total_tax_paise=tax_breakdown.total_tax_paise,
            discount_paise=discount_paise,
            total_amount_paise=total_paise,
            line_items=line_items,
        )

        # 9. Calculate Overall Confidence (Weighted Composite)
        weights = {
            "total_amount": 0.35,
            "receipt_date": 0.20,
            "merchant_name": 0.20,
            "gstin": 0.15,
            "taxes": 0.10,
        }
        composite_conf = sum(
            field_confidences.get(k, 0.0) * w for k, w in weights.items()
        )
        overall_conf = Decimal(str(round(composite_conf, 4)))

        receipt_data = StructuredReceiptDataVO(
            merchant_name=merchant,
            gstin=gstin,
            receipt_date=receipt_date.isoformat() if receipt_date else None,
            invoice_number=invoice_number,
            currency="INR",
            subtotal=subtotal_dec,
            subtotal_paise=subtotal_paise,
            taxes=tax_breakdown,
            discount=discount_dec,
            discount_paise=discount_paise,
            total_amount=total_dec,
            total_amount_paise=total_paise,
            payment_method=payment_method,
            payment_reference=payment_ref,
            line_items=line_items,
        )

        return receipt_data, field_confidences, overall_conf, val_status, val_warnings

    @classmethod
    def _extract_gstin(cls, raw_text: str, lines: List[str]) -> Tuple[Optional[str], float]:
        """Extracts and validates 15-character Indian GSTIN."""
        # 1. Search for explicit GSTIN keyword
        match = re.search(
            r"(?:GSTIN|GST No\.?|GST|Tax ID)[\s:#]+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b",
            raw_text,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).upper()
            if is_valid_gstin(candidate):
                return candidate, 0.99

        # 2. General scan across lines
        for line in lines[:15]:  # GSTIN usually in top 15 lines
            match_broad = re.search(
                r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b",
                line.upper(),
            )
            if match_broad:
                candidate = match_broad.group(1)
                if is_valid_gstin(candidate):
                    return candidate, 0.95

        return None, 0.0

    @classmethod
    def _extract_merchant_name(
        cls,
        lines: List[str],
        gstin: Optional[str],
    ) -> Tuple[Optional[str], float]:
        """Identifies primary merchant or establishment name from header lines."""
        # 1. Look for explicit keyword 'Merchant:' or 'Store:'
        for line in lines[:10]:
            match = re.match(r"(?:Merchant|Store|Seller|Vendor|From)[\s:]+(.+)", line, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) >= 3:
                    return candidate, 0.92

        # 2. Scan top lines, skipping generic headers and GSTIN
        for line in lines[:6]:
            cleaned = line.strip()
            if len(cleaned) < 3 or len(cleaned) > 70:
                continue
            is_generic = any(re.match(p, cleaned, re.IGNORECASE) for p in GENERIC_HEADER_PATTERNS)
            if is_generic:
                continue
            if gstin and gstin in cleaned:
                continue
            # If line is mostly alphabetic letters and title/upper case, likely merchant
            if sum(c.isalpha() for c in cleaned) / max(1, len(cleaned)) > 0.6:
                return cleaned, 0.82

        return None, 0.0

    @classmethod
    def _extract_date(cls, raw_text: str, lines: List[str]) -> Tuple[Optional[Any], float]:
        """Detects and parses receipt transaction date."""
        # 1. Explicit Date label
        for line in lines:
            match = re.search(
                r"(?:Date|Dated|Invoice Date|Bill Date|Txn Date)[\s:#]+([0-9\/\.\-]+(?:\s+[A-Za-z]+)?(?:\s+[0-9]{4})?)",
                line,
                re.IGNORECASE,
            )
            if match:
                parsed = parse_indian_date(match.group(1))
                if parsed:
                    return parsed, 0.95

        # 2. Broad regex pattern search in top/bottom sections
        date_candidates = re.findall(
            r"\b([0-3]?[0-9][\/\-\.][0-1]?[0-9][\/\-\.](?:20)?[0-9]{2})\b",
            raw_text,
        )
        for cand in date_candidates:
            parsed = parse_indian_date(cand)
            if parsed:
                return parsed, 0.80

        # ISO format YYYY-MM-DD
        iso_candidates = re.findall(r"\b(20[2-3][0-9]-[0-1][0-9]-[0-3][0-9])\b", raw_text)
        for cand in iso_candidates:
            parsed = parse_indian_date(cand)
            if parsed:
                return parsed, 0.85

        return None, 0.0

    @classmethod
    def _extract_invoice_number(cls, raw_text: str, lines: List[str]) -> Tuple[Optional[str], float]:
        """Extracts invoice, bill, cash memo, or order reference number."""
        patterns = [
            r"(?:Invoice\s*(?:No|Num|Number|#)|Inv\s*#)[\s:#]*([A-Za-z0-9\-\/]+)",
            r"(?:Bill\s*(?:No|Num|Number|#))[\s:#]*([A-Za-z0-9\-\/]+)",
            r"(?:Cash\s*Memo\s*(?:No|#))[\s:#]*([A-Za-z0-9\-\/]+)",
            r"(?:Receipt\s*(?:No|#))[\s:#]*([A-Za-z0-9\-\/]+)",
            r"(?:Order\s*(?:No|Id|#))[\s:#]*([A-Za-z0-9\-\/]+)",
        ]
        for pat in patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if len(val) >= 3 and not val.lower().startswith("date"):
                    return val, 0.90

        return None, 0.0

    @classmethod
    def _extract_total_amount(cls, raw_text: str, lines: List[str]) -> Tuple[Decimal, int, float]:
        """Detects authoritative total amount payable."""
        # High confidence explicit labels
        primary_patterns = [
            r"(?:Total\s*Amount|Grand\s*Total|Net\s*Payable|Total\s*Payable|Bill\s*Total|Amount\s*Paid)[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)",
            r"(?:^|\n)\s*Total[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)",
        ]
        for pat in primary_patterns:
            matches = list(re.finditer(pat, raw_text, re.IGNORECASE))
            if matches:
                # Last total occurrence is usually the final summary
                last_match = matches[-1]
                dec, paise = parse_monetary_amount(last_match.group(1))
                if paise > 0:
                    return dec, paise, 0.96

        return Decimal("0.0000"), 0, 0.0

    @classmethod
    def _extract_subtotal(cls, raw_text: str, lines: List[str]) -> Tuple[Decimal, int, float]:
        """Extracts subtotal or pre-tax amount."""
        patterns = [
            r"(?:Sub\s*Total|Subtotal|Items\s*Total|Taxable\s*Amount|Net\s*Amount)[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)",
        ]
        for pat in patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                dec, paise = parse_monetary_amount(match.group(1))
                if paise > 0:
                    return dec, paise, 0.90

        return Decimal("0.0000"), 0, 0.0

    @classmethod
    def _extract_tax_breakdown(
        cls,
        raw_text: str,
        lines: List[str],
        gstin: Optional[str],
    ) -> Tuple[TaxBreakdownVO, float]:
        """Identifies CGST, SGST, IGST tax breakdown components."""
        cgst_dec, cgst_paise = Decimal("0.0000"), 0
        sgst_dec, sgst_paise = Decimal("0.0000"), 0
        igst_dec, igst_paise = Decimal("0.0000"), 0
        confidence = 0.0

        cgst_pattern = r"CGST(?:\s*(?:@|at)?\s*\([0-9\.]+\s*%\)|\s*(?:@|at)\s*[0-9\.]+\s*%)?[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)"
        cgst_match = re.search(cgst_pattern, raw_text, re.IGNORECASE)
        if cgst_match:
            cgst_dec, cgst_paise = parse_monetary_amount(cgst_match.group(1))
            confidence = max(confidence, 0.90)

        sgst_pattern = r"SGST(?:\s*(?:@|at)?\s*\([0-9\.]+\s*%\)|\s*(?:@|at)\s*[0-9\.]+\s*%)?[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)"
        sgst_match = re.search(sgst_pattern, raw_text, re.IGNORECASE)
        if sgst_match:
            sgst_dec, sgst_paise = parse_monetary_amount(sgst_match.group(1))
            confidence = max(confidence, 0.90)

        igst_pattern = r"IGST(?:\s*(?:@|at)?\s*\([0-9\.]+\s*%\)|\s*(?:@|at)\s*[0-9\.]+\s*%)?[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)"
        igst_match = re.search(igst_pattern, raw_text, re.IGNORECASE)
        if igst_match:
            igst_dec, igst_paise = parse_monetary_amount(igst_match.group(1))
            confidence = max(confidence, 0.90)

        total_tax_paise = cgst_paise + sgst_paise + igst_paise
        total_tax_dec = cgst_dec + sgst_dec + igst_dec

        # Fallback to general 'Total Tax' or 'Tax' if specific components not found
        if total_tax_paise == 0:
            tax_match = re.search(r"(?:Total\s*Tax|Tax\s*Amount)[\s:#]*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)", raw_text, re.IGNORECASE)
            if tax_match:
                total_tax_dec, total_tax_paise = parse_monetary_amount(tax_match.group(1))
                confidence = 0.75

        return (
            TaxBreakdownVO(
                cgst=cgst_dec,
                cgst_paise=cgst_paise,
                sgst=sgst_dec,
                sgst_paise=sgst_paise,
                igst=igst_dec,
                igst_paise=igst_paise,
                total_tax=total_tax_dec,
                total_tax_paise=total_tax_paise,
                gstin=gstin,
            ),
            confidence,
        )

    @classmethod
    def _extract_discount(cls, raw_text: str, lines: List[str]) -> Tuple[Decimal, int, float]:
        """Extracts discount or promotional deductions."""
        patterns = [
            r"(?:Discount|Coupon|Promo|Offer\s*Discount)[\s:#]*[-]?\s*([₹$Rs\.\s]*[0-9,]+(?:\.[0-9]{2})?)",
        ]
        for pat in patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                dec, paise = parse_monetary_amount(match.group(1))
                if paise > 0:
                    return dec, paise, 0.88

        return Decimal("0.0000"), 0, 0.0

    @classmethod
    def _extract_payment_details(
        cls,
        raw_text: str,
        lines: List[str],
    ) -> Tuple[str, Optional[str], float]:
        """Identifies payment channel and transaction reference / UTR."""
        method = PaymentMethod.UNKNOWN.value
        reference = None
        conf = 0.50

        # UPI detection
        if re.search(r"\b(UPI|Google\s*Pay|GPay|PhonePe|Paytm|BHIM)\b", raw_text, re.IGNORECASE):
            method = PaymentMethod.UPI.value
            conf = 0.95
            utr_match = re.search(r"(?:UPI\s*(?:Ref|UTR|Txn\s*ID)|UTR|Ref\s*No)[\s:#]*([0-9]{12})\b", raw_text, re.IGNORECASE)
            if utr_match:
                reference = utr_match.group(1)
        # Card detection
        elif re.search(r"\b(Card|Visa|Mastercard|Rupay|Amex|Credit\s*Card|Debit\s*Card)\b", raw_text, re.IGNORECASE):
            method = PaymentMethod.CARD.value
            conf = 0.90
            card_match = re.search(r"(?:Ending|Card\s*No\.?)[\s:#\*]*([0-9]{4})\b", raw_text, re.IGNORECASE)
            if card_match:
                reference = f"Card ending {card_match.group(1)}"
        # Cash detection
        elif re.search(r"\b(Cash|Paid\s*in\s*Cash|Cash\s*Memo)\b", raw_text, re.IGNORECASE):
            method = PaymentMethod.CASH.value
            conf = 0.85
        # Netbanking
        elif re.search(r"\b(NEFT|RTGS|IMPS|Net\s*Banking)\b", raw_text, re.IGNORECASE):
            method = PaymentMethod.NETBANKING.value
            conf = 0.85

        return method, reference, conf

    @classmethod
    def _extract_line_items(cls, lines: List[str]) -> Tuple[List[DocumentLineItemVO], float]:
        """Scans for individual item descriptions, quantities, and prices."""
        items: List[DocumentLineItemVO] = []

        # Simple table row heuristic: Description followed by numbers (Qty, Price, Amount)
        # e.g.: Paneer Butter Masala         1    280.00    280.00
        row_pattern = re.compile(
            r"^([A-Za-z0-9\s\(\)\-\&]+?)\s+(\d+(?:\.\d+)?)\s+([0-9,]+(?:\.[0-9]{2})?)(?:\s+([0-9,]+(?:\.[0-9]{2})?))?$"
        )

        in_items_section = False
        for line in lines:
            cleaned = line.strip()
            if re.search(r"\b(Item|Description|Product|Particulars)\b", cleaned, re.IGNORECASE) and re.search(r"\b(Qty|Price|Amount|Rate)\b", cleaned, re.IGNORECASE):
                in_items_section = True
                continue

            if in_items_section:
                # Break on subtotal/total
                if re.match(r"^(?:Subtotal|Sub\s*Total|Total|CGST|SGST|Tax|Discount|Paid)", cleaned, re.IGNORECASE):
                    in_items_section = False
                    continue

                m = row_pattern.match(cleaned)
                if m:
                    desc = m.group(1).strip()
                    qty_str = m.group(2)
                    price_str = m.group(3)
                    amount_str = m.group(4) or price_str

                    if len(desc) >= 2 and not any(re.match(p, desc, re.IGNORECASE) for p in GENERIC_HEADER_PATTERNS):
                        try:
                            qty = Decimal(qty_str)
                            u_dec, u_paise = parse_monetary_amount(price_str)
                            a_dec, a_paise = parse_monetary_amount(amount_str)
                            items.append(
                                DocumentLineItemVO(
                                    description=desc,
                                    quantity=qty,
                                    unit_price=u_dec,
                                    unit_price_paise=u_paise,
                                    amount=a_dec,
                                    amount_paise=a_paise,
                                )
                            )
                        except Exception:
                            continue

        conf = 0.85 if items else 0.0
        return items, conf
