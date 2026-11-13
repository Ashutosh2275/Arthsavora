"""
Arthsavora Application Settings & Environment Configuration
Validated configuration with sensible defaults for local development and testing.
Provides strict validation rules in production environments to prevent insecure defaults.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    # Core Application Info
    PROJECT_NAME: str = "ARTHSAVORA"
    VERSION: str = "1.1.0"
    ENVIRONMENT: str = "development"  # development, testing, staging, production
    DEBUG: bool = False

    # Security & JWT Tokens
    SECRET_KEY: str = "arthsavora-dev-insecure-secret-key-change-in-production-12345678"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours default
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # 30 days
    JWT_ISSUER: str = "ARTHSAVORA"
    JWT_AUDIENCE: Optional[str] = None

    # Supabase Auth / External Identity Integration
    SUPABASE_URL: str = "https://example.supabase.co"
    SUPABASE_KEY: str = "supabase-anon-key-placeholder"
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_JWT_ALGORITHM: str = "HS256"
    SUPABASE_RECEIPTS_BUCKET: str = "receipts"

    # CORS Settings (Explicit origins; wildcard with credentials prohibited)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database: PostgreSQL (Single Financial Source of Truth)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "arthsavora"
    DATABASE_URL: Optional[str] = None

    # Database: MongoDB (Legacy compatibility during transition)
    MONGODB_URL: str = "mongodb://localhost:27017/arthsavora"

    # Background Tasks: Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limiting Controls
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_HEALTH: str = "300/minute"

    # Security Headers
    ENABLE_HSTS: bool = False

    # AI & Intelligence: Google GenAI (Gemini)
    GEMINI_API_KEY: str = "gemini-api-key-placeholder"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OCR: Tesseract
    TESSERACT_CMD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str) and v.strip():
            return v
        data = info.data
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "postgres")
        server = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5433)
        db = data.get("POSTGRES_DB", "arthsavora")
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforces critical security constraints when running in production."""
        if self.ENVIRONMENT.lower() == "production":
            if "insecure" in self.SECRET_KEY.lower() or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL: Production deployments require a cryptographically secure SECRET_KEY (minimum 32 characters)."
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CRITICAL: Wildcard CORS origins ('*') are strictly prohibited in production."
                )
            if self.DEBUG:
                raise ValueError("CRITICAL: DEBUG mode must be disabled in production.")
            self.ENABLE_HSTS = True
        return self


settings = Settings()
