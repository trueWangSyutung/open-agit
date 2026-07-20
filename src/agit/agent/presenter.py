"""Agent presenter — formats plans for user display."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from agit.risk.classifier import RiskLevel
from agit.risk.matrix import get_risk_symbol, get_risk_color
from agit.i18n import t
from agit.utils.console import console


def present_plan(steps: list[dict], dry_run: bool = True) -> None:
    """Display an execution plan with risk indicators."""
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("Command", min_width=40)
    table.add_column("Risk", width=10, justify="center")

    for step in steps:
        risk_str = step.get("risk", "LOW")
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            risk = RiskLevel.LOW
        symbol = get_risk_symbol(risk)
        color = get_risk_color(risk)
        cmd = step.get("command", "")
        desc = step.get("description", "")

        risk_display = f"[{color}]{symbol} {risk.value}[/{color}]"
        if desc:
            cmd_display = f"{cmd}\n[dim]{desc}[/dim]"
        else:
            cmd_display = cmd
        table.add_row(str(step.get("id", "")), cmd_display, risk_display)

    title = f"[dim][dry-run][/dim] {t('plan.title')}" if dry_run else t("plan.title")
    console.print(Panel(table, title=title, border_style="blue"))


def present_risk_summary(steps: list[dict]) -> None:
    """Print overall risk summary."""
    risks = [s.get("risk", "LOW") for s in steps]
    if "CRITICAL" in risks:
        console.print(f"[red bold]{t('plan.risk')}: CRITICAL[/red bold]")
    elif "HIGH" in risks:
        console.print(f"[yellow bold]{t('plan.risk')}: HIGH[/yellow bold]")
    else:
        console.print(f"[green]{t('plan.risk')}: LOW[/green]")


def present_step_result(step: dict, result: str) -> None:
    """Display the result of a single step execution."""
    cmd = step.get("command", "")
    if result == "success":
        console.print(f"[green]✓[/green] {cmd}")
    elif result == "failed":
        console.print(f"[red]✗[/red] {cmd}")
    elif result == "skipped":
        console.print(f"[dim]⊘[/dim] {cmd}")
    elif result == "blocked":
        console.print(f"[red]✋[/red] {cmd} — blocked")
