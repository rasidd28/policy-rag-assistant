"""
app/core/logger.py
------------------
Structured logging with PII masking.
Masks email addresses and phone numbers before writing logs.
"""

import logging
import re
from pathlib import Path

import structlog

from app.core.config import settings

# PII patterns to mask in logs
PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b(?:\+91|0)?[6-9]\d{9}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\b\d{12}\b"), "[AADHAR_REDACTED]"),  # Aadhaar-like
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
]


class PIIMaskingProcessor:
    """Structlog processor that masks PII from log entries."""

    def __call__(self, logger, method, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, str):
                for pattern, replacement in PII_PATTERNS:
                    value = pattern.sub(replacement, value)
                event_dict[key] = value
        return event_dict


def setup_logging():
    """Configure structured logging with PII masking."""
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="ISO"),
            PIIMaskingProcessor(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def get_logger(name: str = __name__):
    setup_logging()
    return structlog.get_logger(name)
