"""agit undo — rollback operations."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.config.loader import load_config
from agit.journal.reader import JournalReader
from agit.journal.undo import get_rollback_plan, execute_rollback
from agit.i18n import t
from agit.utils.console import console, print_info, print_warning, print_success, Prompt
from agit.agent.presenter import present_plan

app = typer.Typer(help="Undo agent operations")


@app.callback(invoke_without_command=True)
def undo_cmd(
    ctx: typer.Context,
    step: int = typer.Option(None, "--step", help="Undo specific step"),
    to_ref: str = typer.Option(None, "--to", help="Rollback to specific commit"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview rollback"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    agit_dir = Path.cwd() / ".agit"
    reader = JournalReader(agit_dir)

    last_session = reader.get_last_session()
    if not last_session:
        print_warning(t("undo.no_journal"))
        raise typer.Exit(1)

    plan = get_rollback_plan(last_session)
    if not plan:
        print_warning(t("undo.no_journal"))
        raise typer.Exit(1)

    if step:
        plan = [p for p in plan if p.get("step") == step]
        if not plan:
            print_warning(f"Step {step} not found")
            raise typer.Exit(1)

    print_info(t("undo.preview"))
    present_plan(
        [{"id": i + 1, "command": p["command"], "risk": p.get("risk", "LOW")} for i, p in enumerate(plan)],
        dry_run=True,
    )

    if dry_run:
        return

    choice = Prompt.ask(
        t("undo.confirm"),
        choices=["y", "N"],
        default="N",
        show_choices=True,
    )

    if choice != "y":
        print_info(t("plan.rejected"))
        return

    results = execute_rollback(plan, cwd=str(Path.cwd()), dry_run=False)
    for r in results:
        if r["result"] == "success":
            print_success(f"Executed: {r['command']}")
        elif r["result"] == "blocked":
            print_warning(f"Blocked: {r['command']}")

    print_success(t("undo.done"))
