"""
Input Sanitizer & Injection Defense.

Sanitizes text inputs, search queries, and filenames to protect against:
- Cross-Site Scripting (XSS)
- SQL Injection vectors
- Path Traversal attempts
- Null-byte poisoning
"""

import html
import re

# Regex for stripping dangerous HTML/JS tags and attributes
DANGEROUS_TAGS_RE = re.compile(
    r"<\s*(script|style|iframe|object|embed|applet|meta|link|base|form)[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
SELF_CLOSING_DANGEROUS_TAGS_RE = re.compile(
    r"<\s*(script|style|iframe|object|embed|applet|meta|link|base|form|input)[^>]*?/?>",
    re.IGNORECASE,
)
EVENT_HANDLERS_RE = re.compile(
    r"\b(onload|onerror|onclick|onmouseover|onfocus|onblur|onchange|onsubmit|onkeydown|onkeyup)\s*=",
    re.IGNORECASE,
)
JAVASCRIPT_URI_RE = re.compile(
    r"(javascript|vbscript|data):",
    re.IGNORECASE,
)

# SQL comments and dangerous token patterns for raw queries
SQL_INJECTION_RE = re.compile(
    r"(--|/\*|\*/|;\s*drop\b|;\s*delete\b|;\s*update\b|;\s*insert\b|\bunion\s+select\b)",
    re.IGNORECASE,
)


def sanitize_html(text: str | None) -> str:
    """
    Sanitizes user input by stripping executable scripts and hazardous event handlers.

    Args:
        text: Raw user input text.

    Returns:
        Sanitized text safe for persistence and display.
    """
    if not text:
        return ""

    # 1. Remove null bytes
    cleaned = text.replace("\x00", "")

    # 2. Strip dangerous blocks (<script>...</script>, etc.)
    cleaned = DANGEROUS_TAGS_RE.sub("", cleaned)
    cleaned = SELF_CLOSING_DANGEROUS_TAGS_RE.sub("", cleaned)

    # 3. Strip inline event handlers (onload=..., onerror=...)
    cleaned = EVENT_HANDLERS_RE.sub("data-sanitized=", cleaned)

    # 4. Neutralize javascript: / data: pseudo-protocols
    cleaned = JAVASCRIPT_URI_RE.sub(r"\1-blocked:", cleaned)

    return cleaned.strip()


def sanitize_search_query(query: str | None, max_length: int = 150) -> str:
    """
    Sanitizes candidate and document search strings.

    Args:
        query: Raw query from user.
        max_length: Maximum allowable length (default: 150 chars).

    Returns:
        Cleaned, bounded search query string.
    """
    if not query:
        return ""

    # Strip null bytes and control chars
    cleaned = "".join(ch for ch in query if ch.isprintable() and ch != "\x00")

    # Remove SQL injection sequences
    cleaned = SQL_INJECTION_RE.sub("", cleaned)

    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)

    # Normalize multiple spaces and limit length
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_length]


def sanitize_filename(filename: str | None) -> str:
    """
    Sanitizes an uploaded or exported filename to prevent path traversal and shell injection.
    """
    if not filename:
        return "archivo_seguro.dat"

    # Remove path traversal characters
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.replace("\x00", "").strip()

    # Remove characters outside safe set (alphanumeric, underscores, hyphens, dots, spaces)
    cleaned = re.sub(r"[^\w\.\-\s]", "_", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)  # No double dots

    return cleaned or "archivo_seguro.dat"
