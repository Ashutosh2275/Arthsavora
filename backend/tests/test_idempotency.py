"""
Arthsavora Idempotency Engine Tests
Validates duplicate request detection, in-flight lock enforcement,
fingerprint verification, and response caching.
"""

import pytest
from app.core.exceptions import ConflictException, ValidationException
from app.core.idempotency import InMemoryIdempotencyStore, compute_request_fingerprint


def test_idempotency_store_acquisition_and_caching():
    """Verifies that the first request acquires a lock and subsequent requests receive cached response."""
    store = InMemoryIdempotencyStore(default_ttl_seconds=3600)
    scope = "user_123"
    idempotency_key = "tx_create_abc"
    fingerprint = compute_request_fingerprint("POST", "/api/v1/transactions", b'{"amount": 500}')

    # 1. First request acquires lock
    is_new, cached = store.check_or_lock(scope, idempotency_key, fingerprint)
    assert is_new is True
    assert cached is None

    # 2. Store completed response
    store.store_response(
        scope=scope,
        idempotency_key=idempotency_key,
        status_code=201,
        content={"id": "tx_999", "amount": 500},
    )

    # 3. Subsequent request with identical fingerprint returns cached response
    is_new, cached = store.check_or_lock(scope, idempotency_key, fingerprint)
    assert is_new is False
    assert cached is not None
    assert cached["status_code"] == 201
    assert cached["content"]["id"] == "tx_999"


def test_idempotency_concurrent_request_raises_conflict():
    """Verifies that an in-flight duplicate request raises ConflictException (409)."""
    store = InMemoryIdempotencyStore(default_ttl_seconds=3600)
    scope = "user_456"
    idempotency_key = "batch_import_xyz"
    fingerprint = compute_request_fingerprint("POST", "/api/v1/imports", b'{"file_id": "f_1"}')

    # First request begins processing
    store.check_or_lock(scope, idempotency_key, fingerprint)

    # Second concurrent duplicate arrives while first is still in-flight
    with pytest.raises(ConflictException) as exc_info:
        store.check_or_lock(scope, idempotency_key, fingerprint)

    assert exc_info.value.code == "CONCURRENT_REQUEST"


def test_idempotency_fingerprint_mismatch_raises_validation_error():
    """Verifies that reusing an idempotency key with different payload is rejected."""
    store = InMemoryIdempotencyStore(default_ttl_seconds=3600)
    scope = "user_789"
    idempotency_key = "payment_key_1"
    fingerprint_original = compute_request_fingerprint("POST", "/api/v1/payments", b'{"amount": 100}')
    fingerprint_tampered = compute_request_fingerprint("POST", "/api/v1/payments", b'{"amount": 500}')

    # Acquire and store original
    store.check_or_lock(scope, idempotency_key, fingerprint_original)
    store.store_response(scope, idempotency_key, 200, {"status": "ok"})

    # Attempt reuse with tampered amount
    with pytest.raises(ValidationException) as exc_info:
        store.check_or_lock(scope, idempotency_key, fingerprint_tampered)

    assert exc_info.value.code == "IDEMPOTENCY_FINGERPRINT_MISMATCH"
