"""Context-aware risk assessment based on repository state."""

from __future__ import annotations

import fnmatch

from agit.risk.classifier import RiskLevel
from agit.git.repo import Repository, RepoStatus
from agit.config.schema import RiskConfig


def assess_contextual_risk(
    command: str,
    base_risk: RiskLevel,
    repo: Repository,
    status: RepoStatus,
    config: RiskConfig,
) -> RiskLevel:
    """Adjust risk level based on current repository context."""
    risk = base_risk
    cmd_lower = command.lower().strip()

    if status.branch and repo.is_protected_branch(status.branch, config.protected_branches):
        if any(kw in cmd_lower for kw in ("commit", "push")):
            risk = _upgrade(risk, RiskLevel.CRITICAL)

    if status.is_dirty:
        if any(kw in cmd_lower for kw in ("checkout", "switch")):
            risk = _upgrade(risk, RiskLevel.HIGH)

    if status.has_conflicts:
        if any(kw in cmd_lower for kw in ("merge", "rebase")):
            risk = _upgrade(risk, RiskLevel.CRITICAL)

    if status.ahead > 50:
        if "push" in cmd_lower:
            risk = _upgrade(risk, RiskLevel.HIGH)

    if "push" in cmd_lower and repo.is_protected_branch(
        status.branch, config.protected_branches
    ):
        risk = _upgrade(risk, RiskLevel.CRITICAL)

    return risk


def _upgrade(current: RiskLevel, target: RiskLevel) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    ci = order.index(current)
    ti = order.index(target)
    return target if ti > ci else current
