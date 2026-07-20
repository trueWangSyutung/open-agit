"""Journal reader — reads execution logs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class JournalReader:
    def __init__(self, agit_dir: Path):
        self.agit_dir = agit_dir
        self.history_dir = agit_dir / "history"

    def get_index(self) -> list[dict[str, Any]]:
        index_path = self.history_dir / "index.json"
        if not index_path.exists():
            return []
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)

    def get_last_session(self) -> dict[str, Any] | None:
        index = self.get_index()
        if not index:
            return None
        last = index[-1]
        return self.get_session(last["session_id"])

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for filepath in sorted(self.history_dir.glob("*.json")):
            if filepath.name == "index.json":
                continue
            with open(filepath, encoding="utf-8") as f:
                sessions = json.load(f)
            for s in sessions:
                if s.get("session_id") == session_id:
                    return s
        return None

    def get_sessions_by_date(self, date_str: str) -> list[dict[str, Any]]:
        filepath = self.history_dir / f"{date_str}.json"
        if not filepath.exists():
            return []
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    def get_recent_sessions(self, count: int = 10) -> list[dict[str, Any]]:
        index = self.get_index()
        recent = index[-count:] if len(index) > count else index
        sessions = []
        for entry in reversed(recent):
            s = self.get_session(entry["session_id"])
            if s:
                sessions.append(s)
        return sessions
