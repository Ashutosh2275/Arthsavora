"""
Arthsavora Core Application Exceptions
Standardized error structures across all domain modules.
Includes specialized security, authentication, and tenant isolation exceptions.
"""

from typing import Any, Dict, List, Optional
from fastapi import status


class ArthsavoraException(Exception):
    """Base exception for all domain and operational errors in Arthsavora."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class NotFoundException(ArthsavoraException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(message, code=code, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(ArthsavoraException):
    """Raised when authentication is missing or invalid."""

    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(message, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredException(UnauthorizedException):
    """Raised specifically when a JWT has expired."""

    def __init__(self, message: str = "Authentication token has expired", code: str = "TOKEN_EXPIRED"):
        super().__init__(message, code=code)


class InvalidTokenException(UnauthorizedException):
    """Raised when a JWT signature, format, or claims validation fails."""

    def __init__(self, message: str = "Invalid authentication token", code: str = "INVALID_TOKEN"):
        super().__init__(message, code=code)


class AccountDisabledException(UnauthorizedException):
    """Raised when a user account is inactive, locked, or suspended."""

    def __init__(self, message: str = "User account is suspended or disabled", code: str = "ACCOUNT_DISABLED"):
        super().__init__(message, code=code)


class AccountDeletedException(UnauthorizedException):
    """Raised when a user account has been soft-deleted."""

    def __init__(self, message: str = "User account has been deleted", code: str = "ACCOUNT_DELETED"):
        super().__init__(message, code=code)


class ForbiddenException(ArthsavoraException):
    """Raised when the user does not have permission to access the resource."""

    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN"):
        super().__init__(message, code=code, status_code=status.HTTP_403_FORBIDDEN)


class InsufficientPermissionsException(ForbiddenException):
    """Raised when a user's workspace role lacks required privileges."""

    def __init__(
        self,
        message: str = "You do not have sufficient permissions to perform this action",
        code: str = "INSUFFICIENT_PERMISSIONS",
    ):
        super().__init__(message, code=code)


class ValidationException(ArthsavoraException):
    """Raised when business logic validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConflictException(ArthsavoraException):
    """Raised when a resource state conflict occurs (e.g. duplicate key)."""

    def __init__(self, message: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(message, code=code, status_code=status.HTTP_409_CONFLICT)


class RateLimitExceededException(ArthsavoraException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str = "Too many requests. Please slow down.", code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(message, code=code, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class DatabaseUnavailableException(ArthsavoraException):
    """Raised when the database connection or health check fails."""

    def __init__(self, message: str = "Database service is temporarily unavailable", code: str = "DATABASE_UNAVAILABLE"):
        super().__init__(message, code=code, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
