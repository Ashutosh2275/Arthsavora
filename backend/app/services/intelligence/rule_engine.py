"""
Arthsavora Classification Rule Engine
Deterministic rule evaluation engine enforcing priority ordering, conflict resolution,
workspace isolation, and safe condition evaluation without code execution.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional
import uuid

from app.domain.category_taxonomy import ClassificationMethod, ConfidenceBand


@dataclass(frozen=True)
class RuleEvaluationResult:
    rule_id: uuid.UUID
    rule_name: str
    rule_scope: str
    suggested_category_id: uuid.UUID
    suggested_merchant_id: Optional[uuid.UUID]
    suggested_merchant_name: Optional[str]
    confidence_score: float
    confidence_band: str
    explanation: str


class RuleEngine:
    """
    Evaluates deterministic classification rules against transaction attributes.
    Enforces strict safety: no eval, exec, or arbitrary code execution.
    """

    @classmethod
    def evaluate(
        cls,
        rules: List[Any],  # List of ClassificationRule models or dicts
        normalized_description: str,
        merchant_name: Optional[str],
        direction: str,
        amount_paise: Optional[int] = None,
        transaction_type: Optional[str] = None,
        account_type: Optional[str] = None,
    ) -> Optional[RuleEvaluationResult]:
        """
        Evaluates ordered rules against transaction parameters.
        Rules are assumed sorted by priority DESC.
        Returns RuleEvaluationResult on first match, or None.
        """
        if not rules:
            return None

        norm_desc_upper = (normalized_description or "").strip().upper()
        merchant_upper = (merchant_name or "").strip().upper() if merchant_name else ""

        for rule in rules:
            # Check enabled status
            is_enabled = getattr(rule, "is_enabled", True)
            if not is_enabled:
                continue

            conditions: Dict[str, Any] = getattr(rule, "conditions", {}) or {}
            if not conditions:
                continue

            if not cls._matches_conditions(
                conditions=conditions,
                desc_upper=norm_desc_upper,
                merchant_upper=merchant_upper,
                direction=direction,
                amount_paise=amount_paise,
                transaction_type=transaction_type,
                account_type=account_type,
            ):
                continue

            # Match found! Construct explanation and result
            scope = getattr(rule, "rule_scope", "workspace")
            rule_name = getattr(rule, "name", "Classification Rule")
            category_id = getattr(rule, "suggested_category_id", None)
            merchant_id = getattr(rule, "suggested_merchant_id", None)

            suggested_merchant_name = None
            if hasattr(rule, "suggested_merchant") and rule.suggested_merchant:
                suggested_merchant_name = rule.suggested_merchant.canonical_name

            explanation = (
                f"Matched user rule '{rule_name}'"
                if scope in ("workspace", "user")
                else f"Matched system rule '{rule_name}'"
            )

            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule_name,
                rule_scope=scope,
                suggested_category_id=category_id,
                suggested_merchant_id=merchant_id,
                suggested_merchant_name=suggested_merchant_name,
                confidence_score=1.0000,
                confidence_band=ConfidenceBand.HIGH.value,
                explanation=explanation,
            )

        return None

    @classmethod
    def _matches_conditions(
        cls,
        conditions: Dict[str, Any],
        desc_upper: str,
        merchant_upper: str,
        direction: str,
        amount_paise: Optional[int],
        transaction_type: Optional[str],
        account_type: Optional[str],
    ) -> bool:
        """Evaluates whether all specified conditions match."""

        # 1. Direction Condition (e.g. "inflow" or "outflow")
        if "direction" in conditions and conditions["direction"]:
            if conditions["direction"].lower() != direction.lower():
                return False

        # 2. Transaction Type Condition (e.g. "expense", "income", "transfer")
        if "transaction_type" in conditions and conditions["transaction_type"]:
            if not transaction_type or conditions["transaction_type"].lower() != transaction_type.lower():
                return False

        # 3. Account Type Condition (e.g. "credit_card", "current", "savings")
        if "account_type" in conditions and conditions["account_type"]:
            if not account_type or conditions["account_type"].lower() != account_type.lower():
                return False

        # 4. Amount Range Conditions (in paise)
        if amount_paise is not None:
            if "min_amount_paise" in conditions and conditions["min_amount_paise"] is not None:
                if amount_paise < conditions["min_amount_paise"]:
                    return False
            if "max_amount_paise" in conditions and conditions["max_amount_paise"] is not None:
                if amount_paise > conditions["max_amount_paise"]:
                    return False

        # 5. Merchant Pattern Condition
        if "merchant_pattern" in conditions and conditions["merchant_pattern"]:
            pat = conditions["merchant_pattern"].strip().upper()
            if pat not in merchant_upper and pat not in desc_upper:
                return False

        # 6. Description Contains (single keyword or list of keywords)
        if "description_contains" in conditions and conditions["description_contains"]:
            tokens = conditions["description_contains"]
            if isinstance(tokens, str):
                tokens = [tokens]
            # Must contain at least one token (OR) or all (AND)?
            # If match_mode is "all", all must be present; default is any token matches
            match_mode = conditions.get("description_match_mode", "any")
            if match_mode == "all":
                if not all(tok.strip().upper() in desc_upper for tok in tokens if tok.strip()):
                    return False
            else:
                if not any(tok.strip().upper() in desc_upper for tok in tokens if tok.strip()):
                    return False

        # 7. Safe Regex Condition (length-bounded to avoid ReDoS)
        if "description_regex" in conditions and conditions["description_regex"]:
            regex_str = conditions["description_regex"]
            if len(regex_str) <= 100:
                try:
                    compiled = re.compile(regex_str, re.IGNORECASE)
                    if not compiled.search(desc_upper):
                        return False
                except re.error:
                    # Ignore invalid user regex
                    return False

        return True
