"""agit commit — AI-assisted commit."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from agit.ai.client import AIClient
from agit.config.loader import load_config
from agit.features.commit import analyze_staged_changes, create_commit, regenerate_commit_message
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_success, print_error, Prompt

app = typer.Typer(help="AI-assisted commit message generation")


@app.callback(invoke_without_command=True)
def commit_cmd(
    ctx: typer.Context,
    message: str = typer.Option(None, "--message", "-m", help="Use provided message"),
    amend: bool = typer.Option(False, "--amend", help="Amend last commit"),
    signoff: bool = typer.Option(False, "--signoff", help="Add Signed-off-by"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    cwd = str(Path.cwd())
    config = load_config(project_dir=Path.cwd())
    repo = Repository(Path.cwd())

    if message:
        if amend:
            create_commit(message, cwd=cwd, signoff=signoff, amend=True)
        else:
            create_commit(message, cwd=cwd, signoff=signoff)
        print_success(t("commit.committed", message=message))
        return

    client = AIClient(config.ai)
    print_info(t("commit.analyzing"))

    data = analyze_staged_changes(config, client, repo)

    if "error" in data:
        print_error(data["error"])
        raise typer.Exit(1)

    full_message = data.get("full_message", "")
    console.print(Panel(
        f"[bold]{data.get('type', '')}({data.get('scope', '')}): {data.get('subject', '')}[/bold]\n\n"
        f"{data.get('body', '')}\n\n"
        f"[dim]{data.get('footer', '')}[/dim]",
        title=t("commit.proposal_title"),
        border_style="blue",
    ))

    while True:
        choice = Prompt.ask(
            "Action",
            choices=["y", "e", "r", "n"],
            default="y",
            show_choices=True,
        )

        if choice == "y":
            if config.commit.auto_stage:
                from agit.git.executor import run_git
                run_git("add", "-u", cwd=cwd, check=False)
            create_commit(
                full_message,
                cwd=cwd,
                signoff=signoff or config.commit.signoff,
                amend=amend,
            )
            print_success(t("commit.committed", message=full_message))
            break
        elif choice == "e":
            edited = Prompt.ask("Enter commit message", default=full_message)
            create_commit(edited, cwd=cwd, signoff=signoff or config.commit.signoff, amend=amend)
            print_success(t("commit.committed", message=edited))
            break
        elif choice == "r":
            print_info("Regenerating...")
            data = regenerate_commit_message(config, client, full_message, repo)
            full_message = data.get("full_message", full_message)
            console.print(f"\n[bold]New proposal:[/bold]\n{full_message}\n")
        else:
            print_info(t("plan.rejected"))
            break
