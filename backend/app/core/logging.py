"""
Arthsavora Logging Configuration
Structured, standard logging for institutional fintech operations.
"""

import logging
import sys

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures root and application loggers with consistent formatting."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("ARTHSAVORA")
    logger.setLevel(level)
    return logger

logger = setup_logging()
