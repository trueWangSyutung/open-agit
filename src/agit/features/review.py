"""AI code review feature."""

from __future__ import annotations

from agit.ai.client import AIClient
from agit.ai.prompts.review import review_prompt
from agit.ai.sanitizer import sanitize_diff, truncate_diff
from agit.config.schema import AgitConfig
from agit.git.diff import get_staged_diff, get_unstaged_diff, get_range_diff, get_commit_diff, DiffResult
from agit.git.executor import run_git
from agit.git.repo import Repository
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
        f"Staged: {len(status.staged_files)} files",
        f"Branches:\n{branches.stdout.strip() or '(none)'}",
    ])


def review_staged(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
) -> dict:
    """Review staged changes. Returns JSON."""
    cwd = str(repo.path)
    diff_result = get_staged_diff(cwd=cwd)
    return _do_review(config, ai_client, repo, diff_result, cwd)


def review_all(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
) -> dict:
    """Review all changes (staged + unstaged). Returns JSON."""
    cwd = str(repo.path)
    diff_result = get_full_diff(cwd)
    return _do_review(config, ai_client, repo, diff_result, cwd)


def review_commit(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    commit_ref: str,
) -> dict:
    """Review a specific commit. Returns JSON."""
    cwd = str(repo.path)
    diff_result = get_commit_diff(commit_ref, cwd=cwd)
    return _do_review(config, ai_client, repo, diff_result, cwd)


def review_range(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    from_ref: str,
    to_ref: str,
) -> dict:
    """Review a range of commits. Returns JSON."""
    cwd = str(repo.path)
    diff_result = get_range_diff(from_ref, to_ref, cwd=cwd)
    return _do_review(config, ai_client, repo, diff_result, cwd)


def _do_review(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    diff_result: DiffResult,
    cwd: str | None = None,
) -> dict:
    if diff_result.file_count == 0:
        return {"issues": [], "good_practices": [], "summary": {"critical": 0, "warning": 0, "suggestion": 0, "overall": "No changes to review"}}

    diff_text = _get_diff_patch(cwd)
    sanitized, _ = sanitize_diff(diff_text)
    truncated, _ = truncate_diff(sanitized)

    repo_context = _get_repo_context(repo)
    locale = config.changelog.locale
    messages = review_prompt(truncated, locale=locale, repo_context=repo_context)
    result = ai_client.chat_json(messages=messages, temperature=0.2)

    result["_diff_summary"] = diff_result.summary
    result["_file_count"] = diff_result.file_count
    return result


def _get_diff_patch(cwd: str | None = None) -> str:
    result = run_git("diff", "--cached", "--patch", cwd=cwd, check=False)
    return result.stdout


def get_full_diff(cwd: str | None = None) -> DiffResult:
    from agit.git.diff import get_full_diff as _get_full_diff
    return _get_full_diff(cwd)
