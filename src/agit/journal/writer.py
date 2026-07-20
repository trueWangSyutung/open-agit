"""Journal writer — records execution logs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JournalWriter:
    def __init__(self, agit_dir: Path):
        self.agit_dir = agit_dir
        self.history_dir = agit_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, trigger: str, intent: str, mode: str = "interactive") -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        session = {
            "session_id": f"sess_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "timestamp": now.isoformat(),
            "trigger": trigger,
            "mode": mode,
            "intent": intent,
            "plan": [],
            "snapshot_before": "",
            "ai_model": "",
            "ai_tokens_used": 0,
            "duration_ms": 0,
            "rollback_plan": [],
        }
        return session

    def add_step(
        self,
        session: dict[str, Any],
        command: str,
        risk: str,
        decision: str,
        result: str,
        commit_hash: str | None = None,
    ) -> None:
        step = {
            "step": len(session["plan"]) + 1,
            "command": command,
            "risk": risk,
            "decision": decision,
            "result": result,
        }
        if commit_hash:
            step["commit_hash"] = commit_hash
        session["plan"].append(step)

    def add_rollback(self, session: dict[str, Any], command: str) -> None:
        session["rollback_plan"].append(command)

    def save_session(self, session: dict[str, Any]) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = self.history_dir / f"{today}.json"

        sessions: list[dict] = []
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                sessions = json.load(f)

        sessions.append(session)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)

        self._update_index(session)
        return filepath

    def _update_index(self, session: dict[str, Any]) -> None:
        index_path = self.history_dir / "index.json"
        index: list[dict] = []
        if index_path.exists():
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)

        index.append({
            "session_id": session["session_id"],
            "timestamp": session["timestamp"],
            "trigger": session["trigger"],
            "intent": session["intent"],
        })

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
