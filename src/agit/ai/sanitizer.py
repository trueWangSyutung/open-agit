"""Data sanitization before sending to AI."""

from __future__ import annotations

import re

_DEFAULT_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AKIA****"),
    (r"sk-[a-zA-Z0-9]{48}", "sk-****"),
    (r"ghp_[a-zA-Z0-9]{36}", "ghp_****"),
    (r"glpat-[a-zA-Z0-9\-]{20,}", "glpat-****"),
    (r"xox[bpoas]-[a-zA-Z0-9\-]+", "xox-****"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[PRIVATE_KEY_REMOVED]", re.DOTALL),
    (r"(?:password|passwd|pwd|secret|token|api_?key)\s*[=:]\s*['\"]?([^'\"\n]{8,})", lambda m: f"{m.group(0).split('=')[0].split(':')[0]}=****"),
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer ****"),
    (r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "[JWT_REMOVED]"),
]


def sanitize_diff(diff_text: str, extra_patterns: list[str] | None = None) -> tuple[str, int]:
    """Sanitize sensitive data from diff text.

    Returns (sanitized_text, replacement_count).
    """
    count = 0
    result = diff_text

    for entry in _DEFAULT_PATTERNS:
        if len(entry) == 3:
            pattern, replacement, flags = entry
            new_result, n = re.subn(pattern, replacement, result, flags=flags)
        else:
            pattern, replacement = entry
            new_result, n = re.subn(pattern, replacement, result)
        count += n
        result = new_result

    if extra_patterns:
        for pattern in extra_patterns:
            new_result, n = re.subn(pattern, "[REDACTED]", result)
            count += n
            result = new_result

    return result, count


def truncate_diff(diff_text: str, max_tokens: int = 8000) -> tuple[str, bool]:
    """Truncate diff to fit within token limit.

    Returns (truncated_text, was_truncated).
    """
    estimated_tokens = len(diff_text) // 4
    if estimated_tokens <= max_tokens:
        return diff_text, False

    target_chars = max_tokens * 4
    lines = diff_text.splitlines()
    result: list[str] = []
    current_len = 0
    for line in lines:
        if current_len + len(line) + 1 > target_chars:
            result.append("\n... [TRUNCATED] ...")
            break
        result.append(line)
        current_len += len(line) + 1

    return "\n".join(result), True
