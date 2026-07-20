"""agit sync — smart synchronization."""

from __future__ import annotations

from pathlib import Path

import typer
import shlex

from agit.config.loader import load_config
from agit.features.sync import analyze_sync_plan, get_sync_status_text
from agit.git.repo import Repository
from agit.git.executor import run_git
from agit.risk.classifier import RiskLevel
from agit.agent.gate import RiskGate
from agit.i18n import t
from agit.utils.console import console, print_info, print_warning, print_success, Prompt

app = typer.Typer(help="Smart sync with remote")


@app.callback(invoke_without_command=True)
def sync_cmd(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview only"),
) -> None:
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

    if not steps or (len(steps) == 1 and steps[0].get("command", "").startswith("#")):
        print_success(t("sync.up_to_date"))
        return

    from agit.agent.presenter import present_plan
    present_plan(steps, dry_run=dry_run)

    if config.agent.solo and not dry_run:
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

    gate = RiskGate(config, repo)
    locale = config.changelog.locale
    context = {
        "branch": status.branch,
        "remote": status.remote_name,
        "remote_url": status.remote_url,
        "ahead": status.ahead,
        "behind": status.behind,
        "staged": len(status.staged_files),
    }

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
            console.print(f"\n[red bold]CRITICAL: {cmd}[/red bold]")
            confirmed = gate.confirm_critical(cmd, locale=locale, context=context)
            if not confirmed:
                print_warning("Skipped")
                continue

        if dry_run:
            print_info(f"[dry-run] Would execute: {cmd}")
            continue

        parts = shlex.split(cmd)
        result = run_git(*parts[1:], cwd=cwd, check=False)
        if result.ok:
            print_success(cmd)
            if result.stdout.strip():
                console.print(result.stdout.rstrip())
        else:
            console.print(f"[red]Failed: {result.stderr}[/red]")

    print_success(t("sync.done"))


def print_error(msg: str) -> None:
    from agit.utils.console import error_console
    error_console.print(f"[red]✗[/red] {msg}")
