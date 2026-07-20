"""Risk matrix definition with configurable policies."""

from __future__ import annotations

from agit.risk.classifier import RiskLevel
from agit.config.schema import RiskConfig


def get_policy(risk: RiskLevel, config: RiskConfig) -> str:
    """Get the policy for a risk level. Returns 'auto', 'confirm', or 'forbid'."""
    if risk == RiskLevel.LOW:
        return "auto"
    if risk == RiskLevel.MEDIUM:
        return "auto"
    if risk == RiskLevel.HIGH:
        return "confirm"
    return "forbid"


def should_block(
    command: str,
    risk: RiskLevel,
    solo: bool,
    config: RiskConfig,
) -> tuple[bool, str]:
    """Determine if a command should be blocked.

    Returns (blocked, reason).
    Only CRITICAL operations are blocked and require confirmation.
    """
    if risk == RiskLevel.CRITICAL:
        return True, f"CRITICAL operation requires confirmation: {command}"

    cmd_lower = command.lower().strip()

    if "force" in cmd_lower and config.force_push == "forbid":
        return True, f"Force push is forbidden by policy"

    if "reset --hard" in cmd_lower and config.reset_hard == "forbid":
        return True, f"Hard reset is forbidden by policy"

    return False, ""


def get_risk_symbol(risk: RiskLevel) -> str:
    symbols = {
        RiskLevel.LOW: "✓",
        RiskLevel.MEDIUM: "✓",
        RiskLevel.HIGH: "▸",
        RiskLevel.CRITICAL: "✋",
    }
    return symbols.get(risk, "?")


def get_risk_color(risk: RiskLevel) -> str:
    colors = {
        RiskLevel.LOW: "green",
        RiskLevel.MEDIUM: "green",
        RiskLevel.HIGH: "yellow",
        RiskLevel.CRITICAL: "red",
    }
    return colors.get(risk, "white")
