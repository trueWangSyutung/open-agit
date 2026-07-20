"""Terminal output utilities with Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

console = Console()
error_console = Console(stderr=True)


def print_plan(steps: list[dict], dry_run: bool = True) -> None:
    """Display an execution plan with risk indicators."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Command", min_width=40)
    table.add_column("Risk", width=8, justify="center")

    risk_symbols = {
        "LOW": "[green]✓[/green]",
        "MEDIUM": "[green]✓[/green]",
        "HIGH": "[yellow]▸[/yellow]",
        "CRITICAL": "[red]✋[/red]",
    }

    for i, step in enumerate(steps, 1):
        risk = step.get("risk", "LOW")
        symbol = risk_symbols.get(risk, "?")
        cmd = step.get("command", "")
        table.add_row(str(i), cmd, symbol)

    prefix = "[dim][dry-run][/dim] " if dry_run else ""
    console.print(Panel(table, title=f"{prefix}Plan", border_style="blue"))


def print_risk_summary(steps: list[dict]) -> None:
    """Print overall risk summary."""
    risks = [s.get("risk", "LOW") for s in steps]
    if "CRITICAL" in risks:
        console.print("[red bold]Risk: CRITICAL[/red bold]")
    elif "HIGH" in risks:
        console.print("[yellow bold]Risk: HIGH[/yellow bold]")
    else:
        console.print("[green]Risk: LOW[/green]")


def ask_approval(steps: list[dict], dry_run: bool = True) -> str:
    """Ask user for approval. Returns y/N/e/a."""
    print_plan(steps, dry_run)
    print_risk_summary(steps)
    console.print()
    choice = Prompt.ask(
        "Approve?",
        choices=["y", "N", "e", "a", "d", "m"],
        default="N",
        show_choices=True,
    )
    return choice


def print_success(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def print_warning(msg: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {msg}")


def print_error(msg: str) -> None:
    error_console.print(f"[red]✗[/red] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[dim]→[/dim] {msg}")


def print_header(title: str) -> None:
    console.print(f"\n[bold]{title}[/bold]")
    console.print("─" * len(title))
