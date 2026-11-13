"""
Arthsavora Domain Layer Exceptions
Pure business rule violations, invariant failures, and domain-level validation errors.
Independent of HTTP transport, web frameworks, or persistence mechanisms.
"""

from typing import Any, Dict, List, Optional


class DomainError(Exception):
    """Base exception for all core business rule and domain invariant violations."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DomainValidationError(DomainError):
    """Raised when a value object or entity attribute violates structural domain rules."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_VALIDATION_ERROR",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        d = details or {}
        if field:
            d["field"] = field
        super().__init__(message, code=code, details=d)


class CurrencyMismatchError(DomainError):
    """Raised when an operation combines two Money instances with different currencies."""

    def __init__(
        self,
        currency_a: str,
        currency_b: str,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"Cannot operate on Money with differing currencies: '{currency_a}' and '{currency_b}'."
        )
        super().__init__(
            message=msg,
            code="CURRENCY_MISMATCH",
            details={"currency_a": currency_a, "currency_b": currency_b},
        )


class BusinessRuleViolationError(DomainError):
    """Raised when an action violates an explicit fintech invariant."""

    def __init__(
        self,
        rule_name: str,
        message: str,
        code: str = "BUSINESS_RULE_VIOLATION",
        details: Optional[Dict[str, Any]] = None,
    ):
        d = details or {}
        d["rule"] = rule_name
        super().__init__(message, code=code, details=d)


class EntityNotFoundError(DomainError):
    """Raised when an authoritative domain entity is not found within the expected boundary."""

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        message: Optional[str] = None,
    ):
        msg = message or f"{entity_type} with ID '{entity_id}' not found."
        super().__init__(
            message=msg,
            code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )


class UnauthorizedDomainActionError(DomainError):
    """Raised when a domain command is executed by an actor lacking necessary domain capability."""

    def __init__(
        self,
        action: str,
        reason: str,
        code: str = "UNAUTHORIZED_DOMAIN_ACTION",
    ):
        super().__init__(
            message=f"Action '{action}' is prohibited: {reason}",
            code=code,
            details={"action": action, "reason": reason},
        )
