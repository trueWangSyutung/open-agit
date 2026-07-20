"""agit replay — replay historical sessions."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.config.loader import load_config
from agit.git.executor import run_git
from agit.journal.reader import JournalReader
from agit.i18n import t
from agit.utils.console import console, print_info, print_success, print_warning, Prompt
from agit.agent.presenter import present_plan

app = typer.Typer(help="Replay historical agent sessions")


@app.callback(invoke_without_command=True)
def replay_cmd(
    ctx: typer.Context,
    date: str = typer.Argument(None, help="Date to replay (YYYY-MM-DD)"),
    session_id: str = typer.Option(None, "--session", help="Session ID to replay"),
    steps: str = typer.Option(None, "--steps", help="Comma-separated step numbers"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    agit_dir = Path.cwd() / ".agit"
    reader = JournalReader(agit_dir)

    if session_id:
        target_session = reader.get_session(session_id)
    elif date:
        sessions = reader.get_sessions_by_date(date)
        target_session = sessions[-1] if sessions else None
    else:
        target_session = reader.get_last_session()

    if not target_session:
        print_warning(t("replay.no_journal"))
        raise typer.Exit(1)

    plan = target_session.get("plan", [])
    if not plan:
        print_warning(t("replay.no_journal"))
        raise typer.Exit(1)

    if steps:
        step_nums = [int(s.strip()) for s in steps.split(",")]
        plan = [p for p in plan if p.get("step") in step_nums]

    print_info(t("replay.found", count=len(plan)))

    present_plan(
        [{"id": p.get("step", i + 1), "command": p.get("command", ""), "risk": p.get("risk", "LOW")} for i, p in enumerate(plan)],
        dry_run=dry_run,
    )

    if dry_run:
        return

    choice = Prompt.ask(
        t("plan.approve"),
        choices=["y", "N"],
        default="N",
        show_choices=True,
    )

    if choice != "y":
        print_info(t("plan.rejected"))
        return

    for p in plan:
        cmd = p.get("command", "")
        if not cmd or cmd.startswith("#"):
            continue

        print_info(t("replay.executing", step=p.get("step", "?")))
        parts = cmd.split()
        if parts[0] == "git":
            result = run_git(*parts[1:], cwd=str(Path.cwd()), check=False)
            if result.ok:
                print_success(cmd)
            else:
                print_warning(f"Failed: {result.stderr}")

    print_success(t("replay.done"))
