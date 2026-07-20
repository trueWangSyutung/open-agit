"""Undo / rollback logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agit.git.executor import run_git
from agit.risk.classifier import classify_command, RiskLevel
from agit.utils.console import console, print_info, print_warning, print_error
from agit.i18n import t


def get_rollback_plan(session: dict[str, Any]) -> list[dict[str, str]]:
    """Generate rollback commands from a journal session."""
    plan: list[dict[str, str]] = []

    for step in reversed(session.get("plan", [])):
        cmd = step.get("command", "")
        result = step.get("result", "")

        if result != "success":
            continue

        if "commit" in cmd and "git commit" in cmd:
            plan.append({
                "command": "git reset --soft HEAD~1",
                "original": cmd,
                "risk": "MEDIUM",
            })
        elif "push" in cmd and "git push" in cmd:
            if "--force" in cmd:
                plan.append({
                    "command": "# Manual revert needed for force push",
                    "original": cmd,
                    "risk": "CRITICAL",
                })
            else:
                sha = step.get("commit_hash", "HEAD")
                plan.append({
                    "command": f"git revert {sha}",
                    "original": cmd,
                    "risk": "HIGH",
                })
        elif "add" in cmd and "git add" in cmd:
            plan.append({
                "command": "git reset HEAD",
                "original": cmd,
                "risk": "LOW",
            })
        elif "tag" in cmd and "git tag" in cmd:
            tag_name = _extract_tag(cmd)
            if tag_name:
                plan.append({
                    "command": f"git tag -d {tag_name}",
                    "original": cmd,
                    "risk": "MEDIUM",
                })

    if session.get("rollback_plan"):
        plan = [{"command": c, "original": "", "risk": classify_command(c).value} for c in session["rollback_plan"]]

    return plan


def execute_rollback(
    plan: list[dict[str, str]],
    cwd: str | None = None,
    dry_run: bool = True,
) -> list[dict[str, str]]:
    """Execute a rollback plan."""
    results = []
    for step in plan:
        cmd = step["command"]
        if cmd.startswith("#"):
            print_warning(cmd)
            results.append({**step, "result": "skipped"})
            continue

        risk = classify_command(cmd)
        if risk == RiskLevel.CRITICAL:
            print_warning(t("risk.solo_blocked", command=cmd))
            results.append({**step, "result": "blocked"})
            continue

        if dry_run:
            print_info(f"[dry-run] Would execute: {cmd}")
            results.append({**step, "result": "dry-run"})
            continue

        parts = cmd.split()
        result = run_git(*parts[1:], cwd=cwd, check=False)
        if result.ok:
            print_info(f"Executed: {cmd}")
            results.append({**step, "result": "success"})
        else:
            print_error(f"Failed: {cmd} — {result.stderr}")
            results.append({**step, "result": "failed"})

    return results


def _extract_tag(cmd: str) -> str | None:
    parts = cmd.split()
    for i, p in enumerate(parts):
        if p == "tag" and i + 1 < len(parts) and not parts[i + 1].startswith("-"):
            return parts[i + 1]
    return None
