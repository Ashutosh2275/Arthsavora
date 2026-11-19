# ARTHSAVORA — Configuration Validation and Startup Security Gates

## 1. Automated Configuration Validation

ARTHSAVORA enforces **fail-fast configuration gates** at the earliest microsecond of application initialization. If any configuration variable fails integrity, cryptographic strength, or environment security rules, the application aborts immediately with a descriptive `ValueError` and prevents the container from accepting traffic.

## 2. Validation Implementation Details

Validation is performed in `backend/app/core/config.py` using Pydantic V2 `@model_validator(mode="after")`:

```python
@model_validator(mode="after")
def validate_production_security(self) -> "Settings":
    """Enforces critical security constraints when running in production."""
    if self.ENVIRONMENT.lower() == "production":
        # 1. Cryptographic Key Strength
        if "insecure" in self.SECRET_KEY.lower() or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "CRITICAL: Production deployments require a cryptographically secure SECRET_KEY (minimum 32 characters)."
            )
        # 2. CORS Boundary Protection
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CRITICAL: Wildcard CORS origins ('*') are strictly prohibited in production."
            )
        # 3. Debug Flag Lock
        if self.DEBUG:
            raise ValueError("CRITICAL: DEBUG mode must be disabled in production.")
        # 4. Enforce HSTS
        self.ENABLE_HSTS = True
    return self
```

## 3. Verified Validation Test Matrix

The configuration gates are covered by unit tests in `backend/tests/test_production_operational_readiness.py`:

| Test Name | Test Assertion | Status |
| :--- | :--- | :--- |
| `test_production_config_rejects_insecure_secret_key` | Raises `ValidationError` when `SECRET_KEY` contains `"insecure"` in `production` | **PASSED** |
| `test_production_config_rejects_short_secret_key` | Raises `ValidationError` when `SECRET_KEY` has length `< 32` in `production` | **PASSED** |
| `test_production_config_rejects_wildcard_cors` | Raises `ValidationError` when `CORS_ORIGINS` contains `"*"` in `production` | **PASSED** |
| `test_production_config_rejects_debug_mode` | Raises `ValidationError` when `DEBUG=True` in `production` | **PASSED** |
| `test_production_config_enforces_hsts_and_validates` | Automatically activates `ENABLE_HSTS=True` in valid `production` | **PASSED** |

## 4. Pre-Deployment Configuration Verification Script

Prior to updating ECS task definitions, CI/CD runs a preflight check:
```bash
python -c "from app.core.config import Settings; import os; os.environ['ENVIRONMENT']='production'; Settings()"
```
If exit code is non-zero, deployment terminates before container spinning.

## 5. Cross-Reference Links
- Secrets Configuration: [SECRETS_AND_ENVIRONMENT_CONFIGURATION.md](file:///d:/Arthsavora/docs/SECRETS_AND_ENVIRONMENT_CONFIGURATION.md)
- Production Readiness Checklist: [PRODUCTION_READINESS_CHECKLIST.md](file:///d:/Arthsavora/docs/PRODUCTION_READINESS_CHECKLIST.md)
