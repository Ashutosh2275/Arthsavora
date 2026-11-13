"""
Configuration and Environment Tests
"""

from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.PROJECT_NAME == "ARTHSAVORA"
    assert settings.ENVIRONMENT == "development"
    assert len(settings.CORS_ORIGINS) > 0
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440
    assert settings.DATABASE_URL is not None
    assert "postgresql+asyncpg://" in settings.DATABASE_URL


def test_cors_origins_not_wildcard():
    settings = Settings()
    # Invariant: wildcard with credentials is prohibited
    assert "*" not in settings.CORS_ORIGINS
