"""AI-assisted commit feature."""

from __future__ import annotations

from agit.ai.client import AIClient
from agit.ai.prompts.commit import commit_prompt, commit_amend_prompt
from agit.ai.sanitizer import sanitize_diff, truncate_diff
from agit.config.schema import AgitConfig
from agit.git.diff import get_staged_diff
from agit.git.executor import run_git
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_error
from agit.utils.errors import GitError


def _get_repo_context(repo: Repository) -> str:
    status = repo.get_status()
    cwd = str(repo.path)
    head = run_git("rev-parse", "--short", "HEAD", cwd=cwd, check=False)
    return "\n".join([
        f"Branch: {status.branch}",
        f"HEAD: {head.output}",
        f"Remote: {status.remote_name} ({status.remote_url})",
        f"Staged files: {len(status.staged_files)}",
    ])


def analyze_staged_changes(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
) -> dict:
    """Analyze staged changes and generate a commit message proposal. Returns JSON."""
    cwd = str(repo.path)
    diff_result = get_staged_diff(cwd=cwd)
    if diff_result.file_count == 0:
        return {"error": t("commit.no_changes")}

    diff_text = _get_diff_text(cwd)
    sanitized, _ = sanitize_diff(diff_text)
    truncated, _ = truncate_diff(sanitized)

    repo_context = _get_repo_context(repo)
    messages = commit_prompt(truncated, repo_context=repo_context)
    result = ai_client.chat_json(messages=messages, temperature=0.4)

    result["_diff_summary"] = diff_result.summary
    result["_file_count"] = diff_result.file_count
    return result


def create_commit(
    message: str,
    cwd: str | None = None,
    signoff: bool = False,
    amend: bool = False,
) -> str:
    """Create a git commit. Returns the commit hash."""
    args = ["commit", "-m", message]
    if signoff:
        args.append("--signoff")
    if amend:
        args.append("--amend")

    result = run_git(*args, cwd=cwd)
    return result.output


def regenerate_commit_message(
    config: AgitConfig,
    ai_client: AIClient,
    current_message: str,
    repo: Repository,
) -> dict:
    """Regenerate commit message. Returns JSON."""
    cwd = str(repo.path)
    diff_text = _get_diff_text(cwd)
    sanitized, _ = sanitize_diff(diff_text)
    truncated, _ = truncate_diff(sanitized)

    repo_context = _get_repo_context(repo)
    messages = commit_amend_prompt(truncated, current_message, repo_context=repo_context)
    return ai_client.chat_json(messages=messages, temperature=0.5)


def _get_diff_text(cwd: str | None = None) -> str:
    result = run_git("diff", "--cached", "--patch", cwd=cwd, check=False)
    return result.stdout
