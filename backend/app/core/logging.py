"""
Arthsavora Logging Configuration & Observability Framework
Structured JSON logging for institutional fintech operations with automated PII/credential scrubbing.
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict

# Sensitive keys and patterns to redact
SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "cookie",
    "pan",
    "aadhaar",
    "cvv",
    "card_number",
    "account_number",
    "secret_key",
    "client_secret",
}

REDACTION_MASK = "[REDACTED]"
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
CARD_PATTERN = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")


def sanitize_value(key: str, value: Any) -> Any:
    """Recursively scrub sensitive keys and patterns from log records."""
    if not isinstance(key, str):
        key = str(key)

    lower_key = key.lower()
    if any(s in lower_key for s in SENSITIVE_KEYS):
        return REDACTION_MASK

    if isinstance(value, dict):
        return {k: sanitize_value(k, v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_value(key, item) for item in value]
    elif isinstance(value, str):
        # Scrub Bearer tokens and potential PANs from string representations
        cleaned = BEARER_PATTERN.sub("Bearer [REDACTED]", value)
        cleaned = CARD_PATTERN.sub("****-****-****-****", cleaned)
        return cleaned
    return value


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with standard telemetry fields."""

    def __init__(self, service_name: str = "ARTHSAVORA", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include contextual attributes if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "workspace_id"):
            log_entry["workspace_id"] = record.workspace_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = {k: sanitize_value(k, v) for k, v in record.extra_data.items()}

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = False,
    environment: str = "development",
) -> logging.Logger:
    """Configures root and application loggers with structured or readable formatting."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if json_format or environment.lower() in ("production", "staging"):
        formatter = StructuredJsonFormatter(service_name="ARTHSAVORA", environment=environment)
    else:
        log_format = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"
        formatter = logging.Formatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    logger = logging.getLogger("ARTHSAVORA")
    logger.setLevel(level)
    return logger


logger = setup_logging()
