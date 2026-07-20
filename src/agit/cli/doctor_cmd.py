"""agit doctor — repository health check."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table
from rich.panel import Panel

from agit.config.loader import load_config
from agit.features.doctor import run_doctor, auto_fix
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_success, print_warning, print_error

app = typer.Typer(help="Repository health check")


@app.callback(invoke_without_command=True)
def doctor_cmd(
    ctx: typer.Context,
    quick: bool = typer.Option(False, "--quick", "-q", help="Quick check (skip AI)"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Auto-fix fixable issues"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    config = load_config(project_dir=Path.cwd())
    repo = Repository(Path.cwd())

    print_info(t("doctor.running"))

    report = run_doctor(config, repo, quick=quick)

    _display_report(report)

    if fix and report.get("fixable"):
        actions = auto_fix(config, repo, cwd=str(Path.cwd()))
        for action in actions:
            print_success(action)
        print_success(t("doctor.fix_done"))


def _display_report(report: dict) -> None:
    table = Table(title=t("doctor.title"), show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Check", min_width=25)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Detail", min_width=20)

    status_symbols = {
        "ok": "[green]✓[/green]",
        "warning": "[yellow]⚠[/yellow]",
        "critical": "[red]●[/red]",
    }

    for i, check in enumerate(report.get("checks", []), 1):
        status = check.get("status", "ok")
        symbol = status_symbols.get(status, "?")
        table.add_row(
            str(i),
            check.get("name", ""),
            symbol,
            check.get("detail", ""),
        )

    console.print(table)

    score = report.get("score", 0)
    if score >= 80:
        score_style = "green"
    elif score >= 60:
        score_style = "yellow"
    else:
        score_style = "red"

    console.print(f"\n[{score_style} bold]{t('doctor.score', score=score)}[/{score_style} bold]")

    fixable = report.get("fixable", [])
    if fixable:
        console.print(f"\n[bold]{t('doctor.auto_fix')}:[/bold]")
        for item in fixable:
            console.print(f"  ✓ {item.get('name', '')}: {item.get('detail', '')}")

    manual = report.get("manual", [])
    if manual:
        console.print(f"\n[bold]{t('doctor.manual_fix')}:[/bold]")
        for item in manual:
            console.print(f"  ! {item.get('name', '')}: {item.get('detail', '')}")
