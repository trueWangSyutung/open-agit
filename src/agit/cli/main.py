"""agit — AI-Powered Git CLI main entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.panel import Panel

from agit import __version__
from agit.i18n import t, set_locale
from agit.utils.console import console, print_error
from agit.utils.errors import AgitError, handle_error

app = typer.Typer(
    name="agit",
    help="AI-Powered Git CLI — Git's AI copilot",
    invoke_without_command=True,
)

# Register subcommands
from agit.cli.init import app as init_app
from agit.cli.config import app as config_app
from agit.cli.changelog_cmd import app as changelog_app
from agit.cli.commit_cmd import app as commit_app
from agit.cli.sync_cmd import app as sync_app
from agit.cli.explain_cmd import app as explain_app
from agit.cli.review_cmd import app as review_app
from agit.cli.doctor_cmd import app as doctor_app
from agit.cli.agent_cmd import app as agent_app
from agit.cli.undo_cmd import app as undo_app
from agit.cli.replay_cmd import app as replay_app
from agit.cli.remote_cmd import app as remote_app
from agit.cli.add_cmd import app as add_app

app.add_typer(init_app, name="init")
app.add_typer(config_app, name="config")
app.add_typer(changelog_app, name="changelog")
app.add_typer(commit_app, name="commit")
app.add_typer(sync_app, name="sync")
app.add_typer(explain_app, name="explain")
app.add_typer(review_app, name="review")
app.add_typer(doctor_app, name="doctor")
app.add_typer(agent_app, name="agent")
app.add_typer(undo_app, name="undo")
app.add_typer(replay_app, name="replay")
app.add_typer(remote_app, name="remote")
app.add_typer(add_app, name="add")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    locale: str = typer.Option(None, "--locale", "-l", help="Set locale (zh_CN, en_US)"),
    dry_run: bool = typer.Option(None, "--dry-run", help="Global dry-run override"),
) -> None:
    """agit — AI-Powered Git CLI.

    Git's AI copilot. The reins always stay in human hands.
    """
    if version:
        console.print(f"agit {__version__}")
        # 打印 符号字 agit 
        console.print(Panel(t("agit")))
        
        raise typer.Exit()

    if locale:
        set_locale(locale)

    if ctx.invoked_subcommand is None and not version:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command("version", hidden=True)
def version_cmd() -> None:
    console.print(f"agit {__version__}")


def run() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except AgitError as e:
        handle_error(e)
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        sys.exit(130)
    except Exception as e:
        handle_error(e)


if __name__ == "__main__":
    run()
