"""
app/core/security.py
---------------------
Security utilities:
 - Prompt injection detection and sanitization
 - Input validation
 - PII masking
"""

import re

from app.core.logger import get_logger

logger = get_logger(__name__)

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(your\s+)?system\s+prompt",
    r"forget\s+(all\s+|your\s+)?previous",
    r"you\s+are\s+now\s+(a\s+)?(?!an\s+AI|a\s+policy)",
    r"reveal\s+(your\s+)?(api\s+key|secret|password|token|prompt)",
    r"print\s+(your\s+)?(system\s+prompt|instructions)",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"act\s+as\s+DAN\b",
    r"bypass\s+(safety|restrictions|guidelines)",
    r"jailbreak",
    r"DAN\s+mode",
    r"<\|im_start\|>|<\|im_end\|>",  # token injection
    r"\[INST\]|\[/INST\]",  # Llama token injection
    r"### (Human|Assistant):",  # format confusion
]

INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)


def detect_prompt_injection(text: str) -> bool:
    """Returns True if the text appears to contain a prompt injection attempt."""
    return bool(INJECTION_REGEX.search(text))


def sanitize_user_input(user_input: str) -> tuple[str, bool]:
    """
    Sanitize user input.
    Returns (sanitized_input, was_flagged).
    If flagged, the caller should refuse the query.
    """
    if not isinstance(user_input, str):
        return "", True

    # Trim whitespace, limit length
    cleaned = user_input.strip()[:2000]

    if detect_prompt_injection(cleaned):
        logger.warning("prompt_injection_detected", input_preview=cleaned[:100])
        return cleaned, True

    return cleaned, False


def sanitize_document_content(content: str) -> str:
    """
    Treat retrieved document content as untrusted.
    Strip any injection-like patterns from document text
    before passing to the LLM context window.
    """
    # Remove common injection markers from document content
    sanitized = re.sub(r"<\|im_(start|end)\|>", "", content)
    sanitized = re.sub(r"\[INST\]|\[/INST\]", "", sanitized)
    sanitized = re.sub(r"### (Human|Assistant):", "", sanitized)
    return sanitized


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format (alphanumeric + hyphens, max 64 chars)."""
    return bool(re.match(r"^[a-zA-Z0-9_-]{1,64}$", session_id or ""))
