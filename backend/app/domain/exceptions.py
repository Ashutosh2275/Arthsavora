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
        self.rule_name = rule_name
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


class UnbalancedJournalError(DomainError):
    """Raised when a journal entry's total debits do not equal total credits."""

    def __init__(
        self,
        total_debits: Any,
        total_credits: Any,
        difference: Any,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"Unbalanced journal entry: Total debits ({total_debits}) must equal total credits ({total_credits}). Difference: {difference}"
        )
        super().__init__(
            message=msg,
            code="UNBALANCED_JOURNAL_ENTRY",
            details={
                "total_debits": str(total_debits),
                "total_credits": str(total_credits),
                "difference": str(difference),
            },
        )


class PeriodClosedError(DomainError):
    """Raised when attempting to post a journal entry to a closed accounting period."""

    def __init__(
        self,
        period_name: str,
        entry_date: Any,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"Cannot post to closed accounting period '{period_name}' for entry date {entry_date}."
        )
        super().__init__(
            message=msg,
            code="ACCOUNTING_PERIOD_CLOSED",
            details={"period_name": period_name, "entry_date": str(entry_date)},
        )


class ImmutableJournalError(DomainError):
    """Raised when attempting to modify, delete, or re-post an immutable posted journal entry."""

    def __init__(
        self,
        entry_number: str,
        status: str,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"Journal entry '{entry_number}' in status '{status}' is immutable and cannot be altered or re-posted."
        )
        super().__init__(
            message=msg,
            code="IMMUTABLE_JOURNAL_ENTRY",
            details={"entry_number": entry_number, "status": status},
        )


class SystemAccountProtectedError(DomainError):
    """Raised when attempting to delete or alter a system-critical chart-of-accounts ledger account."""

    def __init__(
        self,
        account_code: str,
        account_name: str,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"Ledger account '{account_code}' ({account_name}) is a protected system account and cannot be deleted or re-classified."
        )
        super().__init__(
            message=msg,
            code="SYSTEM_ACCOUNT_PROTECTED",
            details={"account_code": account_code, "account_name": account_name},
        )


class ImportProcessingError(DomainError):
    """Raised when statement processing or parsing fails critically."""

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        d = details or {}
        if job_id:
            d["job_id"] = str(job_id)
        super().__init__(message=message, code="IMPORT_PROCESSING_ERROR", details=d)


class InvalidFileFormatError(DomainError):
    """Raised when an uploaded file cannot be parsed or violates structural formats."""

    def __init__(
        self,
        message: str,
        format_detected: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        d = details or {}
        if format_detected:
            d["format_detected"] = format_detected
        super().__init__(message=message, code="INVALID_FILE_FORMAT", details=d)


class FileTooLargeError(DomainError):
    """Raised when an uploaded statement file exceeds the maximum allowed payload size."""

    def __init__(
        self,
        file_size: int,
        max_size: int,
        message: Optional[str] = None,
    ):
        msg = (
            message
            or f"File size of {file_size} bytes exceeds maximum allowed limit of {max_size} bytes (10MB)."
        )
        super().__init__(
            message=msg,
            code="FILE_TOO_LARGE",
            details={"file_size": file_size, "max_size": max_size},
        )


class UnsafeFileError(DomainError):
    """Raised when an uploaded file fails cryptographic, MIME, or magic signature security verification."""

    def __init__(
        self,
        message: str,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        d = details or {}
        if reason:
            d["reason"] = reason
        super().__init__(message=message, code="UNSAFE_FILE_DETECTED", details=d)


class DuplicateImportError(DomainError):
    """Raised when an identical statement file (by SHA-256 hash) has already been processed."""

    def __init__(
        self,
        file_hash: str,
        existing_job_id: str,
        message: Optional[str] = None,
    ):
        msg = message or f"Identical file has already been uploaded in job '{existing_job_id}'."
        super().__init__(
            message=msg,
            code="DUPLICATE_IMPORT_FILE",
            details={"file_hash": file_hash, "existing_job_id": str(existing_job_id)},
        )

