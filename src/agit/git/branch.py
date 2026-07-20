"""Git branch operations."""

from __future__ import annotations

from dataclasses import dataclass, field

from agit.git.executor import run_git


@dataclass
class Branch:
    name: str = ""
    is_current: bool = False
    upstream: str = ""
    ahead: int = 0
    behind: int = 0


def list_branches(cwd: str | None = None) -> list[Branch]:
    result = run_git("branch", "-vv", cwd=cwd, check=False)
    if not result.ok:
        return []

    branches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        is_current = line.startswith("*")
        line = line.lstrip("* ").strip()
        parts = line.split()
        if not parts:
            continue
        branch = Branch(name=parts[0], is_current=is_current)
        if len(parts) >= 3:
            branch.upstream = parts[2].strip("[]")
            if len(parts) >= 4:
                ahead_behind = parts[3]
                if "ahead" in ahead_behind:
                    branch.ahead = int(ahead_behind.split("ahead")[1].strip().rstrip("]"))
                if "behind" in ahead_behind:
                    branch.behind = int(ahead_behind.split("behind")[1].strip().rstrip("]"))
        branches.append(branch)
    return branches


def create_branch(name: str, cwd: str | None = None) -> None:
    run_git("branch", name, cwd=cwd)


def delete_branch(name: str, force: bool = False, cwd: str | None = None) -> None:
    flag = "-D" if force else "-d"
    run_git("branch", flag, name, cwd=cwd)


def checkout(name: str, cwd: str | None = None) -> None:
    run_git("checkout", name, cwd=cwd)


def switch(name: str, cwd: str | None = None) -> None:
    run_git("switch", name, cwd=cwd)
