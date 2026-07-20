"""Repository state inspection and operations."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from agit.git.executor import run_git
from agit.utils.errors import GitError


@dataclass
class RepoStatus:
    branch: str = ""
    is_detached: bool = False
    is_dirty: bool = False
    has_untracked: bool = False
    staged_files: list[str] = field(default_factory=list)
    unstaged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    has_conflicts: bool = False
    conflicted_files: list[str] = field(default_factory=list)
    remote_name: str = ""
    remote_url: str = ""


class Repository:
    def __init__(self, path: str | Path | None = None):
        if path is None:
            path = Path.cwd()
        self.path = Path(path).resolve()
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        result = run_git("rev-parse", "--git-dir", cwd=str(self.path), check=False)
        if not result.ok:
            raise GitError("Not a Git repository")

    def get_status(self) -> RepoStatus:
        status = RepoStatus()

        branch_result = run_git("branch", "--show-current", cwd=str(self.path), check=False)
        status.branch = branch_result.output
        if not status.branch:
            status.is_detached = True
            head_result = run_git("rev-parse", "--short", "HEAD", cwd=str(self.path), check=False)
            status.branch = head_result.output

        status_result = run_git("status", "--porcelain=v1", cwd=str(self.path), check=False)
        for line in status_result.stdout.strip().splitlines():
            if not line:
                continue
            code = line[:2]
            filename = line[3:]
            if code == "??":
                status.untracked_files.append(filename)
                status.has_untracked = True
            elif code in ("UU", "AA", "DD"):
                status.conflicted_files.append(filename)
                status.has_conflicts = True
            else:
                if code[0] != " ":
                    status.staged_files.append(filename)
                if code[1] != " ":
                    status.unstaged_files.append(filename)

        status.is_dirty = bool(status.staged_files or status.unstaged_files or status.has_conflicts)

        tracking = run_git(
            "rev-list", "--left-right", "--count", "HEAD...@{upstream}",
            cwd=str(self.path), check=False,
        )
        if tracking.ok and tracking.output:
            parts = tracking.output.split()
            if len(parts) == 2:
                status.ahead = int(parts[0])
                status.behind = int(parts[1])

        remote_result = run_git("remote", cwd=str(self.path), check=False)
        remotes = remote_result.output.splitlines()
        if remotes:
            status.remote_name = remotes[0]
            url_result = run_git("remote", "get-url", remotes[0], cwd=str(self.path), check=False)
            status.remote_url = url_result.output

        return status

    def get_current_branch(self) -> str:
        result = run_git("branch", "--show-current", cwd=str(self.path))
        return result.output

    def get_head_sha(self, short: bool = True) -> str:
        args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
        result = run_git(*args, cwd=str(self.path), check=False)
        return result.output if result.ok else "(no commits)"

    def is_protected_branch(self, branch: str, protected: list[str]) -> bool:
        for pattern in protected:
            if fnmatch.fnmatch(branch, pattern):
                return True
        return False

    def get_stash_count(self) -> int:
        result = run_git("stash", "list", cwd=str(self.path), check=False)
        if not result.ok or not result.output:
            return 0
        return len(result.output.splitlines())

    def get_orphan_branches(self, protected: list[str]) -> list[str]:
        result = run_git("branch", "--format=%(refname:short)", cwd=str(self.path), check=False)
        if not result.ok:
            return []
        branches = result.output.splitlines()
        tracked_result = run_git(
            "for-each-ref", "--format=%(refname:short) %(upstream:short)",
            "refs/heads/", cwd=str(self.path), check=False,
        )
        tracked = set()
        for line in tracked_result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1]:
                tracked.add(parts[0])
        return [b for b in branches if b not in tracked and not self.is_protected_branch(b, protected)]
