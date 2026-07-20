"""agit agent — interactive agent mode."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.ai.client import AIClient
from agit.agent.engine import AgentEngine
from agit.config.loader import load_config
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_error

app = typer.Typer(help="Interactive AI agent for complex Git operations")


@app.callback(invoke_without_command=True)
def agent_cmd(
    ctx: typer.Context,
    task: str = typer.Argument(..., help="Task description in natural language"),
    dry_run: bool = typer.Option(None, "--dry-run", help="Override dry-run mode"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    config = load_config(project_dir=Path.cwd())
    client = AIClient(config.ai)
    repo = Repository(Path.cwd())

    engine = AgentEngine(config, client, repo, cwd=str(Path.cwd()))
    session = engine.run(task, dry_run=dry_run)

    if session.get("plan"):
        console.print(f"\n[dim]Session: {session['session_id']}[/dim]")
