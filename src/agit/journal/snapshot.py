"""Repository snapshot management."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agit.git.executor import run_git


class SnapshotManager:
    def __init__(self, agit_dir: Path):
        self.agit_dir = agit_dir
        self.snapshots_dir = agit_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, cwd: str | None = None) -> Path:
        now = datetime.now(timezone.utc)
        snapshot_dir = self.snapshots_dir / now.strftime("%Y-%m-%dT%H:%M:%S")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        head = run_git("rev-parse", "HEAD", cwd=cwd, check=False)
        (snapshot_dir / "HEAD").write_text(head.output)

        reflog = run_git("reflog", "-20", cwd=cwd, check=False)
        (snapshot_dir / "reflog").write_text(reflog.stdout)

        staged = run_git("diff", "--cached", "--stat", cwd=cwd, check=False)
        (snapshot_dir / "staged").write_text(staged.stdout)

        unstaged = run_git("diff", "--stat", cwd=cwd, check=False)
        (snapshot_dir / "unstaged_diff").write_text(unstaged.stdout)

        metadata = {
            "created_at": now.isoformat(),
            "head": head.output,
            "branch": run_git("branch", "--show-current", cwd=cwd, check=False).output,
        }
        (snapshot_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False)
        )

        return snapshot_dir

    def get_latest_snapshot(self) -> Path | None:
        dirs = sorted(self.snapshots_dir.iterdir(), reverse=True)
        return dirs[0] if dirs else None
