"""Git log parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from agit.git.executor import run_git


@dataclass
class Commit:
    sha: str = ""
    short_sha: str = ""
    subject: str = ""
    body: str = ""
    author: str = ""
    author_email: str = ""
    date: str = ""
    type: str = ""
    scope: str = ""
    is_breaking: bool = False


def get_log(
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    max_count: int = 100,
    cwd: str | None = None,
) -> list[Commit]:
    """Get parsed commit log."""
    args = [
        "log",
        "--format=%H|%h|%s|%b|%an|%ae|%ai",
        f"--max-count={max_count}",
    ]
    if from_ref:
        args.append(f"{from_ref}..{to_ref}")
    else:
        args.append(to_ref)

    result = run_git(*args, cwd=cwd, check=False)
    if not result.ok or not result.output:
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 6)
        if len(parts) < 7:
            continue
        commit = Commit(
            sha=parts[0],
            short_sha=parts[1],
            subject=parts[2],
            body=parts[3],
            author=parts[4],
            author_email=parts[5],
            date=parts[6],
        )
        _parse_conventional(commit)
        commits.append(commit)
    return commits


def get_last_tag(cwd: str | None = None) -> str | None:
    result = run_git("describe", "--tags", "--abbrev=0", cwd=cwd, check=False)
    return result.output if result.ok and result.output else None


def get_tags(cwd: str | None = None) -> list[str]:
    result = run_git("tag", "--sort=-creatordate", cwd=cwd, check=False)
    if not result.ok or not result.output:
        return []
    return result.output.splitlines()


def get_changed_files(from_ref: str, to_ref: str, cwd: str | None = None) -> list[str]:
    result = run_git("diff", "--name-only", f"{from_ref}..{to_ref}", cwd=cwd, check=False)
    if not result.ok or not result.output:
        return []
    return result.output.splitlines()


def _parse_conventional(commit: Commit) -> None:
    """Parse conventional commit format: type(scope): subject"""
    subject = commit.subject
    breaking = False
    if subject.startswith("!"):
        breaking = True
        subject = subject[1:]

    if "(" in subject and "): " in subject:
        type_part, rest = subject.split("(", 1)
        scope, subject_text = rest.split("): ", 1)
        commit.type = type_part.strip()
        commit.scope = scope.strip()
        commit.subject = subject_text.strip()
    elif ": " in subject:
        type_part, subject_text = subject.split(": ", 1)
        commit.type = type_part.strip()
        commit.subject = subject_text.strip()

    if breaking or "BREAKING CHANGE" in commit.body:
        commit.is_breaking = True
