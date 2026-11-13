"""
Arthsavora Centralized Rate Limiter
Throttles request volume per remote IP address or authenticated user identity.
Shields authentication and sensitive API endpoints from brute force and denial of service.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings


def get_rate_limit_key(request: Request) -> str:
    """
    Computes rate limit key. Prefers authenticated user sub/id if available;
    falls back to client remote IP address.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request) or "unknown"


# Global SlowAPI Limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    enabled=settings.RATE_LIMIT_ENABLED,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)
