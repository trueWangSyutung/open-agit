"""Subprocess-based safe Git command executor."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from agit.utils.errors import GitError


@dataclass
class GitResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        return self.stdout.strip()


def run_git(*args: str, cwd: str | None = None, check: bool = True) -> GitResult:
    """Run a git command safely via subprocess."""
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        gr = GitResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        if check and not gr.ok:
            raise GitError(f"git {' '.join(args)} failed: {gr.stderr.strip()}")
        return gr
    except FileNotFoundError:
        raise GitError("git is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        raise GitError(f"git {' '.join(args)} timed out")


def run_git_raw(cmd: list[str], cwd: str | None = None, check: bool = True) -> GitResult:
    """Run a raw git command (cmd should include 'git' as first element)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        gr = GitResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        if check and not gr.ok:
            raise GitError(f"{' '.join(cmd)} failed: {gr.stderr.strip()}")
        return gr
    except FileNotFoundError:
        raise GitError("git is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        raise GitError(f"{' '.join(cmd)} timed out")
