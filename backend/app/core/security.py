"""
Arthsavora Security Utilities
Password hashing, verification, JWT token issuance and independent signature validation.
Supports timezone-aware UTC timestamps, distinct token types (access vs refresh),
and dual validation for internal and Supabase-issued tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import uuid
import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt
from app.core.config import settings
from app.core.exceptions import InvalidTokenException, TokenExpiredException


def create_access_token(
    subject: Union[str, Any],
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Encodes a signed JWT access token with timezone-aware expiry and token typing."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "email": email or str(subject),
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
        "nbf": now,
        "jti": str(uuid.uuid4()),
    }
    if settings.JWT_AUDIENCE:
        to_encode["aud"] = settings.JWT_AUDIENCE
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encodes a signed long-lived refresh token strictly tagged with type='refresh'."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "email": email or str(subject),
        "type": "refresh",
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": expire,
        "nbf": now,
        "jti": str(uuid.uuid4()),
    }
    if settings.JWT_AUDIENCE:
        to_encode["aud"] = settings.JWT_AUDIENCE

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(
    token: str,
    expected_type: Optional[str] = "access",
) -> Dict[str, Any]:
    """
    Decodes and independently verifies a JWT token.
    Validates signature, expiration, issuer, and token type.
    Falls back to Supabase JWT secret if configured and internal verification fails.
    """
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_nbf": True,
        "verify_iat": True,
        "verify_aud": bool(settings.JWT_AUDIENCE),
        "require_exp": True,
        "require_iat": True,
    }

    # Attempt decoding with internal primary SECRET_KEY
    payload = None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options=options,
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        # Fall back to SUPABASE_JWT_SECRET if configured (for external Supabase Auth tokens)
        if settings.SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=[settings.SUPABASE_JWT_ALGORITHM],
                    options={"verify_signature": True, "verify_exp": True},
                )
            except ExpiredSignatureError:
                raise TokenExpiredException()
            except JWTError:
                pass

    if payload is None:
        raise InvalidTokenException("Invalid token signature or malformed payload.")

    # Validate token type if specified
    token_type = payload.get("type")
    if expected_type and token_type and token_type != expected_type:
        raise InvalidTokenException(
            f"Invalid token type: expected '{expected_type}', got '{token_type}'."
        )

    # Ensure subject claim is present
    if not payload.get("sub"):
        raise InvalidTokenException("Token is missing subject claim ('sub').")

    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Generates a secure salted bcrypt hash for a plaintext password."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")
