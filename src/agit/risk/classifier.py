"""Static risk classification for git commands."""

from __future__ import annotations

import re
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def classify_command(command: str) -> RiskLevel:
    """Classify a git command's risk level."""
    cmd = command.strip().lower()

    if not cmd.startswith("git"):
        if any(kw in cmd for kw in ["ai", "generate", "analyze", "explain"]):
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    for pattern, risk in _CRITICAL_PATTERNS:
        if re.search(pattern, cmd):
            return RiskLevel.CRITICAL

    for pattern, risk in _HIGH_PATTERNS:
        if re.search(pattern, cmd):
            return RiskLevel.HIGH

    for pattern, risk in _MEDIUM_PATTERNS:
        if re.search(pattern, cmd):
            return RiskLevel.MEDIUM

    return RiskLevel.LOW


_CRITICAL_PATTERNS = [
    (r"push\s+.*--force", RiskLevel.CRITICAL),
    (r"push\s+.*-f\b", RiskLevel.CRITICAL),
    (r"reset\s+--hard", RiskLevel.CRITICAL),
    (r"clean\s+-[fd]", RiskLevel.CRITICAL),
    (r"clean\s+--force", RiskLevel.CRITICAL),
    (r"push\s+.*--delete", RiskLevel.CRITICAL),
    (r"branch\s+.*-D\s+.*origin", RiskLevel.CRITICAL),
    (r"push\s+.*:refs/heads", RiskLevel.CRITICAL),
]

_HIGH_PATTERNS = [
    (r"\bcommit\b", RiskLevel.HIGH),
    (r"\bpush\b", RiskLevel.HIGH),
    (r"\bmerge\b", RiskLevel.HIGH),
    (r"\brebase\b", RiskLevel.HIGH),
    (r"\btag\b", RiskLevel.HIGH),
    (r"branch\s+-d\b", RiskLevel.HIGH),
    (r"branch\s+--delete", RiskLevel.HIGH),
]

_MEDIUM_PATTERNS = [
    (r"\badd\b", RiskLevel.MEDIUM),
    (r"\bstash\b", RiskLevel.MEDIUM),
    (r"\bcheckout\b", RiskLevel.MEDIUM),
    (r"\bswitch\b", RiskLevel.MEDIUM),
    (r"\bbranch\s+(?!-)", RiskLevel.MEDIUM),
]
