"""Repository health check (doctor) feature."""

from __future__ import annotations

import re
from pathlib import Path

from agit.config.schema import AgitConfig
from agit.git.repo import Repository, RepoStatus
from agit.git.executor import run_git
from agit.git.log import get_log
from agit.i18n import t
from agit.utils.console import console


def _get_all_non_ignored_files(repo: Repository) -> list[str]:
    """Get all files not ignored by .gitignore (tracked + untracked)."""
    cwd = str(repo.path)

    tracked = run_git("ls-files", cwd=cwd, check=False)
    tracked_files = tracked.output.splitlines() if tracked.ok and tracked.output else []

    untracked = run_git("ls-files", "--others", "--exclude-standard", cwd=cwd, check=False)
    untracked_files = untracked.output.splitlines() if untracked.ok and untracked.output else []

    seen = set()
    all_files = []
    for f in tracked_files + untracked_files:
        if f and f not in seen:
            seen.add(f)
            all_files.append(f)
    return all_files


def run_doctor(
    config: AgitConfig,
    repo: Repository,
    quick: bool = False,
) -> dict:
    """Run health checks and return JSON report."""
    status = repo.get_status()
    checks: list[dict] = []
    score = 100

    all_files = _get_all_non_ignored_files(repo)

    check = _check_untracked(status)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_large_files(config, repo, all_files)
    checks.append(check)
    if check["status"] != "ok":
        score -= 10

    check = _check_sensitive(config, repo, all_files)
    checks.append(check)
    if check["status"] != "ok":
        score -= 20

    check = _check_binary(config, all_files)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_gitignore(repo)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_conflicts(status)
    checks.append(check)
    if check["status"] != "ok":
        score -= 15

    check = _check_conventional(config, repo)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_remote(repo)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_branch_status(status)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_stash(repo)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_orphan_branches(config, repo)
    checks.append(check)
    if check["status"] != "ok":
        score -= 5

    check = _check_env_files(all_files)
    checks.append(check)
    if check["status"] != "ok":
        score -= 10

    score = max(0, score)

    return {
        "checks": checks,
        "score": score,
        "total_files": len(all_files),
        "fixable": [c for c in checks if c.get("fixable")],
        "manual": [c for c in checks if c["status"] != "ok" and not c.get("fixable")],
    }


def auto_fix(
    config: AgitConfig,
    repo: Repository,
    cwd: str | None = None,
) -> list[str]:
    """Auto-fix fixable issues. Returns list of actions taken."""
    actions: list[str] = []
    gitignore = repo.path / ".gitignore"

    additions = []
    if gitignore.exists():
        content = gitignore.read_text()
    else:
        content = ""

    for pattern in ["*.pyc", "__pycache__/", ".env", "*.pyo"]:
        if pattern not in content:
            additions.append(pattern)

    if additions:
        new_content = content.rstrip() + "\n" + "\n".join(additions) + "\n"
        gitignore.write_text(new_content)
        actions.append(f"Added to .gitignore: {', '.join(additions)}")

    return actions


def _check_untracked(status: RepoStatus) -> dict:
    count = len(status.untracked_files)
    if count == 0:
        return {"name": t("doctor.check.untracked"), "status": "ok", "detail": ""}
    return {
        "name": t("doctor.check.untracked"),
        "status": "warning",
        "detail": f"{count} files: {', '.join(status.untracked_files[:5])}",
    }


def _check_large_files(config: AgitConfig, repo: Repository, all_files: list[str]) -> dict:
    max_bytes = _parse_size(config.doctor.max_file_size)

    large = []
    for f in all_files:
        fpath = repo.path / f
        if fpath.exists() and fpath.stat().st_size > max_bytes:
            size_mb = fpath.stat().st_size / (1024 * 1024)
            large.append(f"{f} ({size_mb:.1f}MB)")

    if not large:
        return {"name": t("doctor.check.large_files"), "status": "ok", "detail": f"Checked {len(all_files)} files"}
    return {"name": t("doctor.check.large_files"), "status": "warning", "detail": ", ".join(large[:5])}


def _check_sensitive(config: AgitConfig, repo: Repository, all_files: list[str]) -> dict:
    patterns = config.doctor.sensitive_patterns
    findings: list[str] = []

    for f in all_files:
        fpath = repo.path / f
        if not fpath.exists() or fpath.stat().st_size > 1_000_000:
            continue
        try:
            content = fpath.read_text(errors="ignore")
        except Exception:
            continue
        for pattern in patterns:
            if re.search(pattern, content):
                findings.append(f"{f}: matches {pattern}")
                break

    if not findings:
        return {"name": t("doctor.check.sensitive"), "status": "ok", "detail": f"Scanned {len(all_files)} files"}
    return {
        "name": t("doctor.check.sensitive"),
        "status": "critical",
        "detail": f"{len(findings)} findings in {len(all_files)} files",
        "fixable": False,
    }


def _check_binary(config: AgitConfig, all_files: list[str]) -> dict:
    extensions = set(config.doctor.binary_extensions)
    binaries = [f for f in all_files if any(f.endswith(ext) for ext in extensions)]
    if not binaries:
        return {"name": t("doctor.check.binary"), "status": "ok", "detail": ""}
    return {"name": t("doctor.check.binary"), "status": "warning", "detail": ", ".join(binaries[:5])}


def _check_gitignore(repo: Repository) -> dict:
    gitignore = repo.path / ".gitignore"
    if not gitignore.exists():
        return {"name": t("doctor.check.gitignore"), "status": "warning", "detail": "Missing .gitignore", "fixable": True}
    content = gitignore.read_text()
    missing = []
    for pattern in ["*.pyc", "__pycache__/", ".env", ".DS_Store"]:
        if pattern not in content:
            missing.append(pattern)
    if missing:
        return {"name": t("doctor.check.gitignore"), "status": "warning", "detail": f"Missing: {', '.join(missing)}", "fixable": True}
    return {"name": t("doctor.check.gitignore"), "status": "ok", "detail": ""}


def _check_conflicts(status: RepoStatus) -> dict:
    if status.has_conflicts:
        return {"name": t("doctor.check.conflicts"), "status": "critical", "detail": f"{len(status.conflicted_files)} files"}
    return {"name": t("doctor.check.conflicts"), "status": "ok", "detail": ""}


def _check_conventional(config: AgitConfig, repo: Repository) -> dict:
    if not config.commit.conventional:
        return {"name": t("doctor.check.conventional"), "status": "ok", "detail": ""}
    commits = get_log(max_count=20, cwd=str(repo.path))
    non_conventional = [c for c in commits if not c.type]
    if not non_conventional:
        return {"name": t("doctor.check.conventional"), "status": "ok", "detail": f"{len(commits)}/{len(commits)} compliant"}
    return {"name": t("doctor.check.conventional"), "status": "warning", "detail": f"{len(non_conventional)}/{len(commits)} non-compliant"}


def _check_remote(repo: Repository) -> dict:
    result = run_git("remote", cwd=str(repo.path), check=False)
    if not result.ok or not result.output:
        return {"name": t("doctor.check.remote"), "status": "warning", "detail": t("git.no_remote")}
    return {"name": t("doctor.check.remote"), "status": "ok", "detail": result.output.splitlines()[0]}


def _check_branch_status(status: RepoStatus) -> dict:
    if status.ahead > 0 or status.behind > 0:
        detail = f"ahead={status.ahead}, behind={status.behind}"
        return {"name": t("doctor.check.branch"), "status": "warning", "detail": detail}
    return {"name": t("doctor.check.branch"), "status": "ok", "detail": ""}


def _check_stash(repo: Repository) -> dict:
    count = repo.get_stash_count()
    if count > 3:
        return {"name": t("doctor.check.stash"), "status": "warning", "detail": f"{count} stashes"}
    return {"name": t("doctor.check.stash"), "status": "ok", "detail": f"{count}"}


def _check_orphan_branches(config: AgitConfig, repo: Repository) -> dict:
    orphans = repo.get_orphan_branches(config.risk.protected_branches)
    if not orphans:
        return {"name": t("doctor.check.orphan"), "status": "ok", "detail": ""}
    return {"name": t("doctor.check.orphan"), "status": "warning", "detail": f"{len(orphans)}: {', '.join(orphans[:3])}"}


def _check_env_files(all_files: list[str]) -> dict:
    """Check if .env files are present in non-ignored files."""
    env_files = [f for f in all_files if f.endswith(".env") or ".env." in f or f == ".env"]
    if not env_files:
        return {"name": "Env files", "status": "ok", "detail": ""}
    return {
        "name": "Env files",
        "status": "critical",
        "detail": f"Found {len(env_files)}: {', '.join(env_files[:3])}",
        "fixable": False,
    }


def _parse_size(size_str: str) -> int:
    size_str = size_str.upper().strip()
    if size_str.endswith("MB"):
        return int(size_str[:-2]) * 1024 * 1024
    if size_str.endswith("KB"):
        return int(size_str[:-2]) * 1024
    if size_str.endswith("GB"):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    return int(size_str)
