"""Git diff parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from agit.git.executor import run_git


@dataclass
class DiffHunk:
    header: str = ""
    lines: list[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0


@dataclass
class FileDiff:
    filename: str = ""
    old_filename: str = ""
    hunks: list[DiffHunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False

    @property
    def summary(self) -> str:
        return f"+{self.additions}/-{self.deletions}"


@dataclass
class DiffResult:
    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def summary(self) -> str:
        return f"{self.file_count} files, +{self.total_additions}/-{self.total_deletions}"


def get_staged_diff(cwd: str | None = None) -> DiffResult:
    return _parse_diff(["diff", "--cached", "--stat", "--patch"], cwd)


def get_unstaged_diff(cwd: str | None = None) -> DiffResult:
    return _parse_diff(["diff", "--stat", "--patch"], cwd)


def get_full_diff(cwd: str | None = None) -> DiffResult:
    return _parse_diff(["diff", "HEAD", "--stat", "--patch"], cwd)


def get_commit_diff(commit: str, cwd: str | None = None) -> DiffResult:
    return _parse_diff(["diff", f"{commit}~1..{commit}", "--stat", "--patch"], cwd)


def get_range_diff(from_ref: str, to_ref: str, cwd: str | None = None) -> DiffResult:
    return _parse_diff(["diff", f"{from_ref}..{to_ref}", "--stat", "--patch"], cwd)


def _parse_diff(args: list[str], cwd: str | None = None) -> DiffResult:
    result = run_git(*args, cwd=cwd, check=False)
    if not result.ok or not result.stdout.strip():
        return DiffResult()

    diff_result = DiffResult()
    current_file: FileDiff | None = None
    current_hunk: DiffHunk | None = None

    for line in result.stdout.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                diff_result.files.append(current_file)
            current_file = FileDiff()
            parts = line.split(" b/")
            if len(parts) >= 2:
                current_file.filename = parts[-1]
        elif line.startswith("--- a/"):
            if current_file:
                current_file.old_filename = line[6:]
        elif line.startswith("--- /dev/null"):
            if current_file:
                current_file.is_new = True
        elif line.startswith("+++ /dev/null"):
            if current_file:
                current_file.is_deleted = True
        elif line.startswith("@@"):
            if current_file and current_hunk:
                current_file.hunks.append(current_hunk)
            current_hunk = DiffHunk(header=line)
        elif line.startswith("+") and not line.startswith("+++"):
            if current_hunk:
                current_hunk.lines.append(line)
                current_hunk.additions += 1
            if current_file:
                current_file.additions += 1
                diff_result.total_additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            if current_hunk:
                current_hunk.lines.append(line)
                current_hunk.deletions += 1
            if current_file:
                current_file.deletions += 1
                diff_result.total_deletions += 1
        elif line.startswith("Binary files"):
            if current_file:
                current_file.is_binary = True

    if current_file:
        if current_hunk:
            current_file.hunks.append(current_hunk)
        diff_result.files.append(current_file)

    return diff_result
