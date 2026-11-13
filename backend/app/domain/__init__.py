"""
Arthsavora Domain Layer Package
Exposes financial value objects, domain events, domain exceptions, and business rules.
"""

from .exceptions import (
    BusinessRuleViolationError,
    CurrencyMismatchError,
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
    UnauthorizedDomainActionError,
)
from .money import Money
from .events import (
    DomainEvent,
    DomainEventCollector,
    create_account_created_event,
    create_journal_posted_event,
    create_member_joined_event,
    create_transaction_created_event,
    create_workspace_created_event,
)
from .rules import (
    validate_ai_prediction_invariants,
    validate_refund_invariants,
    validate_transfer_invariants,
)

__all__ = [
    "BusinessRuleViolationError",
    "CurrencyMismatchError",
    "DomainError",
    "DomainValidationError",
    "EntityNotFoundError",
    "UnauthorizedDomainActionError",
    "Money",
    "DomainEvent",
    "DomainEventCollector",
    "create_account_created_event",
    "create_journal_posted_event",
    "create_member_joined_event",
    "create_transaction_created_event",
    "create_workspace_created_event",
    "validate_ai_prediction_invariants",
    "validate_refund_invariants",
    "validate_transfer_invariants",
]
