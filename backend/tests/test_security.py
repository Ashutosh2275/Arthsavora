"""
Security Utilities Tests
"""

from jose import jwt
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hashing_and_verification():
    raw_password = "SecureSuperPassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_token_creation():
    subject = "user@arthsavora.com"
    token = create_access_token(subject=subject)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == subject
    assert payload["iss"] == settings.PROJECT_NAME
    assert "exp" in payload
    assert "iat" in payload
