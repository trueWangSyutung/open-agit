"""Smart sync feature."""

from __future__ import annotations

from agit.config.schema import AgitConfig
from agit.git.repo import Repository, RepoStatus
from agit.git.executor import run_git
from agit.risk.classifier import RiskLevel
from agit.i18n import t
from agit.utils.console import console, print_info, print_warning


def analyze_sync_plan(
    repo: Repository,
    config: AgitConfig,
) -> list[dict]:
    """Analyze repository state and generate sync plan. Returns list of steps."""
    status = repo.get_status()
    steps: list[dict] = []

    if status.has_conflicts:
        return [{
            "command": "# resolve conflicts manually",
            "description": t("sync.conflict_detected"),
            "risk": "CRITICAL",
        }]

    needs_stash = status.is_dirty and status.behind > 0
    if needs_stash:
        steps.append({
            "command": "git stash push -m 'agit sync auto-stash'",
            "description": t("sync.stashing"),
            "risk": "MEDIUM",
        })

    if status.behind > 0:
        steps.append({
            "command": "git pull --rebase",
            "description": t("sync.pulling"),
            "risk": "HIGH",
        })

    if needs_stash and status.behind > 0:
        steps.append({
            "command": "git stash pop",
            "description": "Restore stashed changes",
            "risk": "MEDIUM",
        })

    if status.ahead > 0:
        remote = status.remote_name or "origin"
        branch = status.branch
        is_protected = repo.is_protected_branch(branch, config.risk.protected_branches)
        risk = "CRITICAL" if is_protected else "HIGH"
        steps.append({
            "command": f"git push {remote} {branch}",
            "description": t("sync.pushing"),
            "risk": risk,
        })

    if not steps:
        steps.append({
            "command": "# up to date",
            "description": t("sync.up_to_date"),
            "risk": "LOW",
        })

    return steps


def get_sync_status_text(status: RepoStatus) -> str:
    """Format sync status as human-readable text."""
    parts: list[str] = []

    if status.ahead > 0:
        parts.append(t("sync.local_ahead", count=status.ahead))
    if status.behind > 0:
        parts.append(t("sync.remote_ahead", count=status.behind))
    if status.is_dirty:
        parts.append(t("sync.has_uncommitted"))
    if not parts:
        parts.append(t("sync.up_to_date"))

    return " | ".join(parts)
