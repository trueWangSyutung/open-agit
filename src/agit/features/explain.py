"""Commit explanation feature."""

from __future__ import annotations

from agit.ai.client import AIClient
from agit.ai.prompts.explain import explain_prompt
from agit.ai.sanitizer import sanitize_diff, truncate_diff
from agit.config.schema import AgitConfig
from agit.git.log import get_log, Commit
from agit.git.diff import get_range_diff, get_commit_diff
from agit.git.repo import Repository
from agit.git.executor import run_git
from agit.i18n import t


def _get_repo_context(repo: Repository) -> str:
    status = repo.get_status()
    cwd = str(repo.path)
    head = run_git("rev-parse", "--short", "HEAD", cwd=cwd, check=False)
    branches = run_git("branch", "-vv", cwd=cwd, check=False)
    return "\n".join([
        f"Branch: {status.branch}",
        f"HEAD: {head.output}",
        f"Remote: {status.remote_name} ({status.remote_url})",
        f"Branches:\n{branches.stdout.strip() or '(none)'}",
    ])


def explain_commits(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
) -> dict:
    """Explain commits using AI. Returns JSON."""
    cwd = str(repo.path)
    commits = get_log(from_ref=from_ref, to_ref=to_ref, cwd=cwd)
    if not commits:
        return {"error": t("explain.no_commits")}

    commit_info = _format_commit_info(commits)

    if from_ref:
        diff_result = get_range_diff(from_ref, to_ref, cwd=cwd)
    else:
        diff_result = get_commit_diff(to_ref, cwd=cwd)

    diff_text = _get_diff_text(from_ref, to_ref, cwd)
    sanitized, _ = sanitize_diff(diff_text)
    truncated, _ = truncate_diff(sanitized)

    repo_context = _get_repo_context(repo)
    locale = config.changelog.locale
    messages = explain_prompt(truncated, commit_info, locale=locale, repo_context=repo_context)
    result = ai_client.chat_json(messages=messages, temperature=0.5)

    result["commit_count"] = len(commits)
    result["file_count"] = diff_result.file_count
    if from_ref:
        result["range"] = f"{from_ref}..{to_ref}"
    else:
        result["range"] = to_ref

    return result


def explain_single_commit(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    commit_sha: str,
) -> dict:
    """Explain a single commit. Returns JSON."""
    cwd = str(repo.path)
    commits = get_log(from_ref=f"{commit_sha}~1", to_ref=commit_sha, cwd=cwd)
    if not commits:
        return {"error": t("explain.no_commits")}

    commit_info = _format_commit_info(commits)
    diff_text = _get_diff_text(f"{commit_sha}~1", commit_sha, cwd)
    sanitized, _ = sanitize_diff(diff_text)
    truncated, _ = truncate_diff(sanitized)

    repo_context = _get_repo_context(repo)
    locale = config.changelog.locale
    messages = explain_prompt(truncated, commit_info, locale=locale, repo_context=repo_context)
    result = ai_client.chat_json(messages=messages, temperature=0.5)
    result["commit_count"] = 1
    result["range"] = commit_sha
    return result


def _format_commit_info(commits: list[Commit]) -> str:
    lines = []
    for c in commits:
        lines.append(f"{c.short_sha} {c.subject}")
        lines.append(f"  Author: {c.author} <{c.author_email}>")
        lines.append(f"  Date: {c.date}")
        if c.body:
            lines.append(f"  Body: {c.body[:300]}")
        lines.append("")
    return "\n".join(lines)


def _get_diff_text(from_ref: str | None, to_ref: str, cwd: str | None = None) -> str:
    if from_ref:
        cmd_args = ["diff", f"{from_ref}..{to_ref}", "--patch"]
    else:
        cmd_args = ["diff", f"{to_ref}~1..{to_ref}", "--patch"]

    result = run_git(*cmd_args, cwd=cwd, check=False)
    return result.stdout
