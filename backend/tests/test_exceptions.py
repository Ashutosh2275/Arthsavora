"""
Exception and Error Handling Tests
"""

import pytest
from app.core.exceptions import (
    ArthsavoraException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)


def test_exception_inheritance_and_defaults():
    exc = NotFoundException("Resource not found")
    assert isinstance(exc, ArthsavoraException)
    assert exc.status_code == 404
    assert exc.code == "NOT_FOUND"
    assert exc.message == "Resource not found"


def test_unauthorized_exception():
    exc = UnauthorizedException()
    assert exc.status_code == 401
    assert exc.code == "UNAUTHORIZED"


def test_validation_exception_with_details():
    details = [{"field": "amount", "issue": "Must be greater than 0"}]
    exc = ValidationException("Invalid payload", details=details)
    assert exc.status_code == 422
    assert exc.code == "VALIDATION_ERROR"
    assert exc.details == details
