"""Changelog generation feature."""

from __future__ import annotations

from pathlib import Path

from agit.ai.client import AIClient
from agit.ai.prompts.changelog import changelog_prompt
from agit.ai.sanitizer import truncate_diff
from agit.config.schema import AgitConfig
from agit.git.log import get_log, get_last_tag, Commit
from agit.git.repo import Repository
from agit.git.executor import run_git
from agit.i18n import t
from agit.utils.console import console, print_info, print_header


def _get_repo_context(repo: Repository) -> str:
    """Build repository context string for prompts."""
    status = repo.get_status()
    cwd = str(repo.path)
    head = run_git("rev-parse", "--short", "HEAD", cwd=cwd, check=False)
    branches = run_git("branch", "-vv", cwd=cwd, check=False)
    tags = run_git("tag", "--sort=-creatordate", cwd=cwd, check=False)
    remotes = run_git("remote", "-v", cwd=cwd, check=False)

    return "\n".join([
        f"Branch: {status.branch}",
        f"HEAD: {head.output}",
        f"Remote: {status.remote_name} ({status.remote_url})",
        f"Tags: {tags.output or '(none)'}",
        f"Branches:\n{branches.stdout.strip() or '(none)'}",
    ])


def generate_changelog(
    config: AgitConfig,
    ai_client: AIClient,
    repo: Repository,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
) -> dict:
    """Generate a changelog from git history using AI. Returns JSON."""
    if from_ref is None:
        from_ref = get_last_tag(cwd=str(repo.path))

    commits = get_log(from_ref=from_ref, to_ref=to_ref, cwd=str(repo.path))
    if not commits:
        return {"error": t("changelog.no_changes"), "sections": {}, "breaking_changes": []}

    commits_text = _format_commits(commits)
    truncated, was_truncated = truncate_diff(commits_text)

    if was_truncated:
        print_info("Truncated commit history to fit token limit")

    repo_context = _get_repo_context(repo)
    locale = config.changelog.locale
    messages = changelog_prompt(truncated, locale=locale, repo_context=repo_context)
    result = ai_client.chat_json(messages=messages, temperature=0.2)

    result["commit_count"] = len(commits)
    if from_ref:
        result["from_ref"] = from_ref
    result["to_ref"] = to_ref

    return result


def format_changelog_markdown(data: dict, sections_config: list[str]) -> str:
    """Format changelog JSON data as Markdown."""
    lines: list[str] = []

    version = data.get("version", "")
    date = data.get("date", "")
    if version:
        lines.append(f"## {version} ({date})")
    else:
        lines.append(f"## Changes ({date})")
    lines.append("")

    if data.get("summary"):
        lines.append(data["summary"])
        lines.append("")

    sections = data.get("sections", {})
    section_titles = {
        "feat": "Features", "fix": "Bug Fixes", "perf": "Performance",
        "refactor": "Refactoring", "docs": "Documentation", "chore": "Chores",
    }

    for section_key in sections_config:
        items = sections.get(section_key, [])
        if not items:
            continue
        title = section_titles.get(section_key, section_key.title())
        lines.append(f"### {title}")
        lines.append("")
        for item in items:
            lines.append(f"- {item.get('title', '')}")
        lines.append("")

    breaking = data.get("breaking_changes", [])
    if breaking:
        lines.append("### Breaking Changes")
        lines.append("")
        for item in breaking:
            lines.append(f"- **{item.get('title', '')}**")
        lines.append("")

    return "\n".join(lines)


def format_changelog_json(data: dict) -> str:
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_commits(commits: list[Commit]) -> str:
    lines = []
    for c in commits:
        prefix = "BREAKING " if c.is_breaking else ""
        scope = f"({c.scope})" if c.scope else ""
        lines.append(f"{c.short_sha} {prefix}{c.type}{scope}: {c.subject}")
        if c.body:
            lines.append(f"  {c.body[:200]}")
    return "\n".join(lines)
