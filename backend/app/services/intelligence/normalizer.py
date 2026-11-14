"""
Arthsavora Transaction Description Normalizer
Deterministic, versioned pipeline for cleaning banking descriptions,
extracting reference tokens, identifying payment channels, and isolating merchant candidates.
"""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class NormalizedDescriptionResult:
    original_description: str
    normalized_description: str
    merchant_candidate: Optional[str]
    extracted_reference: Optional[str]
    payment_channel: str
    normalization_version: str = "v1.0.0"


class DescriptionNormalizer:
    """
    Deterministic rule-based description cleaner optimized for Indian banking statements.
    Preserves original description untouched while generating normalized representations.
    """

    VERSION = "v1.0.0"

    # Known Indian Payment Channels & Regex Patterns
    UPI_CHANNEL_REGEX = re.compile(r"^(?:UPI[/\-_]|UPI\s+|BHIM[/\-_])", re.IGNORECASE)
    POS_CHANNEL_REGEX = re.compile(r"^(?:POS[/\-_]|POS\s+|EDC[/\-_]|SWIPE[/\-_])", re.IGNORECASE)
    NEFT_CHANNEL_REGEX = re.compile(r"^(?:NEFT[/\-_]|NEFT\s+)", re.IGNORECASE)
    IMPS_CHANNEL_REGEX = re.compile(r"^(?:IMPS[/\-_]|IMPS\s+)", re.IGNORECASE)
    RTGS_CHANNEL_REGEX = re.compile(r"^(?:RTGS[/\-_]|RTGS\s+)", re.IGNORECASE)
    ACH_CHANNEL_REGEX = re.compile(r"^(?:ACH[/\-_\s]|NACH[/\-_\s]|ECS[/\-_\s])", re.IGNORECASE)
    ATM_CHANNEL_REGEX = re.compile(r"(?:ATM\s+WDL|CASH\s+WDL|ATM\s+CASH|ATM[/\-_]CWDR)", re.IGNORECASE)

    # VPA / UPI handle pattern (e.g. user@okhdfcbank, merchant@paytm)
    VPA_HANDLE_REGEX = re.compile(r"[\w\.\-]+@(okhdfcbank|okaxis|oksbi|okicici|paytm|apl|ibl|ybl|axl|gpay|icici|hdfcbank|sbi|postbank|jupiteraxis)", re.IGNORECASE)

    # Reference Number Patterns (12-digit UPI RRN, 16-character alphanumeric UTR)
    UPI_RRN_REGEX = re.compile(r"\b(\d{12})\b")
    UTR_REF_REGEX = re.compile(r"\b([A-Z]{4}[A-Z0-9]{7,18}|CMS\d{9,12}|N\d{10,12}|R\d{10,12})\b", re.IGNORECASE)

    # Terminal / City noise tokens common in Indian POS statements
    LOCATION_NOISE_REGEX = re.compile(
        r"\b(?:BANGALORE|BENGALURU|MUMBAI|DELHI|NEW DELHI|HYDERABAD|CHENNAI|PUNE|KOLKATA|AHMEDABAD|GURGAON|GURUGRAM|NOIDA|JAIPUR|IN|IND)\b",
        re.IGNORECASE
    )

    # General Banking Noise Tokens & Prepositions
    BANKING_NOISE_TOKENS = {
        "P2A", "P2M", "BIL", "REV", "DR", "CR", "MB", "INET", "MOB", "TPV", "WDL",
        "TRF", "TXN", "DEP", "CHQ", "REF", "AUTH", "SETTL", "ONLINE", "DIRECT", "PAYMENT",
        "PURCHASE", "RECHARGE", "ECOM", "MERCHANT", "RETAIL", "TRANSFER", "INSTANT",
        "TO", "FOR", "FROM", "VIA", "BY", "IN", "AT", "ON", "OF"
    }

    @classmethod
    def normalize(cls, raw_description: Optional[str]) -> NormalizedDescriptionResult:
        if not raw_description or not raw_description.strip():
            return NormalizedDescriptionResult(
                original_description=raw_description or "",
                normalized_description="UNSPECIFIED TRANSACTION",
                merchant_candidate=None,
                extracted_reference=None,
                payment_channel="general",
                normalization_version=cls.VERSION,
            )

        original = raw_description.strip()
        working = original

        # 1. Determine Payment Channel
        channel = "general"
        if cls.UPI_CHANNEL_REGEX.search(working) or "@" in working or "UPI" in working.upper():
            channel = "upi"
        elif cls.POS_CHANNEL_REGEX.search(working):
            channel = "pos"
        elif cls.NEFT_CHANNEL_REGEX.search(working):
            channel = "neft"
        elif cls.IMPS_CHANNEL_REGEX.search(working):
            channel = "imps"
        elif cls.RTGS_CHANNEL_REGEX.search(working):
            channel = "rtgs"
        elif cls.ACH_CHANNEL_REGEX.search(working):
            channel = "nach_mandate"
        elif cls.ATM_CHANNEL_REGEX.search(working):
            channel = "atm"

        # 2. Extract Reference Tokens Before Stripping
        extracted_ref: Optional[str] = None
        rrn_match = cls.UPI_RRN_REGEX.search(working)
        if rrn_match:
            extracted_ref = rrn_match.group(1)
        else:
            utr_match = cls.UTR_REF_REGEX.search(working)
            if utr_match:
                extracted_ref = utr_match.group(1)

        # 3. Strip Payment Channel Prefixes
        working = re.sub(r"^(?:UPI[/\-_]|POS[/\-_]|NEFT[/\-_]|IMPS[/\-_]|RTGS[/\-_]|ACH[/\-_]|NACH[/\-_]|ECS[/\-_])\s*", "", working, flags=re.IGNORECASE)
        working = re.sub(r"^(?:CR[/\-_]|DR[/\-_]|P2A[/\-_]|P2M[/\-_])\s*", "", working, flags=re.IGNORECASE)

        # 4. Handle Delimited UPI strings (e.g. "UPI/SWIGGY/1234567890/UPI-PAY")
        parts = re.split(r"[/\\|\-_]", working)
        if len(parts) > 1:
            # Filter out pure numbers, noise tokens, and short fragments
            clean_parts = []
            for part in parts:
                p_clean = part.strip()
                if not p_clean:
                    continue
                # If part is pure digits (e.g. 1234567890), it's a reference
                if p_clean.isdigit():
                    if not extracted_ref:
                        extracted_ref = p_clean
                    continue
                # If part is VPA handle
                if cls.VPA_HANDLE_REGEX.search(p_clean):
                    # extract username part of VPA as potential merchant candidate
                    vpa_user = p_clean.split("@")[0].strip()
                    if len(vpa_user) >= 3 and vpa_user.upper() not in cls.BANKING_NOISE_TOKENS:
                        clean_parts.append(vpa_user)
                    continue
                # Ignore isolated banking noise
                if p_clean.upper() in cls.BANKING_NOISE_TOKENS:
                    continue
                clean_parts.append(p_clean)

            if clean_parts:
                working = " ".join(clean_parts)

        # 5. Remove Isolated VPA Handles
        working = cls.VPA_HANDLE_REGEX.sub("", working)

        # 6. Remove POS Terminal ID / Card Digits (e.g. POS-4402, *4092, #9901)
        working = re.sub(r"\b(?:POS\s*\d+|TERM\s*\d+|TID\s*\d+)\b", "", working, flags=re.IGNORECASE)
        working = re.sub(r"[*#]\d{4,8}", "", working)

        # 7. Remove Location Suffixes (e.g. "STARBUCKS BANGALORE IN" -> "STARBUCKS")
        working = cls.LOCATION_NOISE_REGEX.sub("", working)

        # 8. Clean up extra punctuation, symbols, multiple spaces
        working = re.sub(r"[#*@:;,\.]", " ", working)
        working = re.sub(r"\s+", " ", working).strip()

        # 9. Clean Words & Isolate Merchant Candidate
        words = working.split()
        meaningful_words = [w for w in words if w.upper() not in cls.BANKING_NOISE_TOKENS and not w.isdigit()]
        
        # Deduplicate consecutive identical words (e.g. SWIGGY SWIGGY -> SWIGGY)
        deduped = []
        for w in meaningful_words:
            if not deduped or w.upper() != deduped[-1].upper():
                deduped.append(w)
        meaningful_words = deduped

        if meaningful_words:
            normalized_desc = " ".join(meaningful_words).upper()
            merchant_cand = " ".join(meaningful_words[:3]).upper()  # First 1-3 meaningful words represent merchant
        elif working:
            normalized_desc = working.upper()
            merchant_cand = working.upper()
        else:
            normalized_desc = original.upper()
            merchant_cand = None

        # Special Case: ATM Withdrawals
        if channel == "atm":
            normalized_desc = "ATM CASH WITHDRAWAL"
            merchant_cand = None

        return NormalizedDescriptionResult(
            original_description=original,
            normalized_description=normalized_desc,
            merchant_candidate=merchant_cand,
            extracted_reference=extracted_ref,
            payment_channel=channel,
            normalization_version=cls.VERSION,
        )
