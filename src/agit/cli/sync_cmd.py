"""agit sync — smart synchronization."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.config.loader import load_config
from agit.features.sync import analyze_sync_plan, get_sync_status_text
from agit.git.repo import Repository
from agit.git.executor import run_git
from agit.risk.classifier import RiskLevel
from agit.i18n import t
from agit.utils.console import console, print_info, print_warning, print_success, Prompt

app = typer.Typer(help="Smart sync with remote")


@app.callback(invoke_without_command=True)
def sync_cmd(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return

    cwd = str(Path.cwd())
    config = load_config(project_dir=Path.cwd())
    repo = Repository(cwd)

    print_info(t("sync.analyzing"))
    status = repo.get_status()

    console.print(f"Branch: {status.branch}")
    console.print(f"Status: {get_sync_status_text(status)}")

    steps = analyze_sync_plan(repo, config)

    if not steps or steps[0].get("command", "").startswith("#"):
        print_success(t("sync.up_to_date"))
        return

    from agit.agent.presenter import present_plan
    present_plan(steps, dry_run=config.agent.dry_run)

    if config.agent.solo:
        choice = "y"
    else:
        choice = Prompt.ask(
            t("plan.approve"),
            choices=["y", "N"],
            default="N",
            show_choices=True,
        )

    if choice != "y":
        print_info(t("plan.rejected"))
        return

    for step in steps:
        cmd = step.get("command", "")
        if cmd.startswith("#"):
            continue

        risk_str = step.get("risk", "LOW")
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            risk = RiskLevel.LOW

        if risk == RiskLevel.CRITICAL:
            print_warning(t("risk.solo_blocked", command=cmd))
            continue

        if config.agent.dry_run:
            print_info(f"[dry-run] Would execute: {cmd}")
            continue

        parts = cmd.split()
        result = run_git(*parts[1:], cwd=cwd, check=False)
        if result.ok:
            print_success(cmd)
        else:
            print_error(f"Failed: {result.stderr}")

    print_success(t("sync.done"))


def print_error(msg: str) -> None:
    from agit.utils.console import error_console
    error_console.print(f"[red]✗[/red] {msg}")
