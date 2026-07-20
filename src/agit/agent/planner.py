"""Agent task planner with full snapshot context."""

from __future__ import annotations

from agit.ai.client import AIClient
from agit.ai.prompts.planner import planner_prompt, intent_prompt
from agit.config.schema import AgitConfig
from agit.git.repo import Repository
from agit.git.executor import run_git
from agit.i18n import t


def parse_intent(ai_client: AIClient, user_input: str) -> dict:
    """Parse natural language intent into structured format. Returns JSON."""
    messages = intent_prompt(user_input)
    return ai_client.chat_json(messages=messages, temperature=0.3)


def generate_plan(
    ai_client: AIClient,
    config: AgitConfig,
    user_intent: str,
    repo: Repository,
) -> dict:
    """Generate an execution plan from user intent. Returns JSON."""
    status = repo.get_status()
    snapshot = _collect_snapshot(repo)
    repo_state = _format_repo_state(status, repo, config, snapshot)

    locale = config.changelog.locale
    messages = planner_prompt(user_intent, repo_state, locale=locale)
    return ai_client.chat_json(messages=messages, temperature=0.3)


def _collect_snapshot(repo: Repository) -> dict:
    """Collect full repository snapshot data."""
    cwd = str(repo.path)

    head = run_git("rev-parse", "HEAD", cwd=cwd, check=False)
    head_short = run_git("rev-parse", "--short", "HEAD", cwd=cwd, check=False)
    reflog = run_git("reflog", "-10", "--oneline", cwd=cwd, check=False)
    branches = run_git("branch", "-vv", cwd=cwd, check=False)
    tags = run_git("tag", "--sort=-creatordate", cwd=cwd, check=False)
    remotes = run_git("remote", "-v", cwd=cwd, check=False)
    staged = run_git("diff", "--cached", "--stat", cwd=cwd, check=False)
    staged_patch = run_git("diff", "--cached", "--patch", cwd=cwd, check=False)
    unstaged = run_git("diff", "--stat", cwd=cwd, check=False)
    unstaged_patch = run_git("diff", "--patch", cwd=cwd, check=False)
    status_porcelain = run_git("status", "--porcelain=v1", cwd=cwd, check=False)
    log_recent = run_git("log", "--oneline", "-10", "--decorate", cwd=cwd, check=False)

    return {
        "head": head.output,
        "head_short": head_short.output,
        "reflog": reflog.stdout.strip(),
        "branches": branches.stdout.strip(),
        "tags": tags.stdout.strip(),
        "remotes": remotes.stdout.strip(),
        "staged_stat": staged.stdout.strip(),
        "staged_patch": staged_patch.stdout.strip()[:3000],
        "unstaged_stat": unstaged.stdout.strip(),
        "unstaged_patch": unstaged_patch.stdout.strip()[:3000],
        "status_porcelain": status_porcelain.stdout.strip(),
        "recent_log": log_recent.stdout.strip(),
    }


def _format_repo_state(status, repo: Repository, config: AgitConfig, snapshot: dict) -> str:
    lines = [
        "=== Repository State ===",
        f"Branch: {status.branch}",
        f"HEAD: {snapshot['head_short']}",
        f"Detached HEAD: {status.is_detached}",
        f"Working tree dirty: {status.is_dirty}",
        f"Commits ahead of remote: {status.ahead}",
        f"Commits behind remote: {status.behind}",
        f"Has merge conflicts: {status.has_conflicts}",
        "",
        "=== Staged Files ===",
        snapshot["staged_stat"] or "(none)",
        "",
        "=== Unstaged Changes ===",
        snapshot["unstaged_stat"] or "(none)",
        "",
        "=== Untracked Files ===",
        (", ".join(status.untracked_files[:10])) or "(none)",
        "",
        "=== Branches ===",
        snapshot["branches"],
        "",
        "=== Tags (recent) ===",
        snapshot["tags"] or "(none)",
        "",
        "=== Remotes ===",
        snapshot["remotes"] or "(none)",
        "",
        "=== Recent Commits ===",
        snapshot["recent_log"] or "(none)",
        "",
        "=== Reflog ===",
        snapshot["reflog"] or "(none)",
        "",
        "=== Configuration ===",
        f"Protected branches: {', '.join(config.risk.protected_branches)}",
        f"Auto push: {config.agent.auto_push}",
        f"Solo mode: {config.agent.solo}",
        "",
        "=== Command Format Rules ===",
        "- NEVER include --dry-run in git commands",
        "- Push branch: git push {remote} {branch}",
        "- Push tag: git push {remote} {tag_name}",
        "- Create tag: git tag -a {tag_name} -m 'message'",
        "- Commit: git commit -m 'message'",
        "- For release: add -> commit -> tag -> push branch -> push tag",
    ]

    return "\n".join(lines)
