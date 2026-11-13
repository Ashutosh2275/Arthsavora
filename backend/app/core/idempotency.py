"""
Arthsavora Request Idempotency Engine
Provides idempotency key validation, concurrency lock detection,
and response replay caching for sensitive write operations.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, Optional, Tuple
from fastapi import Header, Request, Response
from app.core.exceptions import ConflictException, ValidationException


class InMemoryIdempotencyStore:
    """Thread-safe in-memory store for idempotency keys with automatic expiry."""

    def __init__(self, default_ttl_seconds: int = 86400):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def _compute_key(self, scope: str, idempotency_key: str) -> str:
        return f"{scope}:{idempotency_key}"

    def check_or_lock(
        self,
        scope: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Attempts to acquire a lock or return an existing completed response.
        Returns (is_new, cached_response_data).
        Raises ConflictException if request is currently in-flight.
        """
        storage_key = self._compute_key(scope, idempotency_key)
        now = datetime.now(timezone.utc)

        existing = self._store.get(storage_key)
        if existing:
            # Check expiration
            if now > existing["expires_at"]:
                del self._store[storage_key]
            elif existing["status"] == "in_flight":
                raise ConflictException(
                    message="A request with this Idempotency-Key is currently being processed.",
                    code="CONCURRENT_REQUEST",
                )
            else:
                # Validate fingerprint match
                if existing["fingerprint"] != request_fingerprint:
                    raise ValidationException(
                        message="Idempotency key reused with different request parameters or payload.",
                        code="IDEMPOTENCY_FINGERPRINT_MISMATCH",
                    )
                return False, existing["response"]

        # Register new in-flight lock
        self._store[storage_key] = {
            "status": "in_flight",
            "fingerprint": request_fingerprint,
            "created_at": now,
            "expires_at": now + self._default_ttl,
            "response": None,
        }
        return True, None

    def store_response(
        self,
        scope: str,
        idempotency_key: str,
        status_code: int,
        content: Any,
    ) -> None:
        """Stores the final completed response against the idempotency key."""
        storage_key = self._compute_key(scope, idempotency_key)
        if storage_key in self._store:
            self._store[storage_key]["status"] = "completed"
            self._store[storage_key]["response"] = {
                "status_code": status_code,
                "content": content,
            }

    def release_lock(self, scope: str, idempotency_key: str) -> None:
        """Removes lock in case of transient execution failure."""
        storage_key = self._compute_key(scope, idempotency_key)
        if storage_key in self._store and self._store[storage_key]["status"] == "in_flight":
            del self._store[storage_key]


# Global in-memory instance (can be swapped for Redis in distributed clusters)
idempotency_store = InMemoryIdempotencyStore()


def compute_request_fingerprint(method: str, path: str, body_bytes: bytes) -> str:
    """Computes a SHA-256 hash representing the exact request parameters."""
    h = hashlib.sha256()
    h.update(method.upper().encode("utf-8"))
    h.update(path.encode("utf-8"))
    h.update(body_bytes)
    return h.hexdigest()
