"""agit add — stage files for commit."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.git.executor import run_git
from agit.i18n import t
from agit.utils.console import console, print_success, print_error, print_info

app = typer.Typer(help="Stage files for commit")


@app.callback(invoke_without_command=True)
def add_cmd(
    ctx: typer.Context,
    files: list[str] = typer.Argument(None, help="Files to stage (supports glob patterns)"),
    all: bool = typer.Option(False, "--all", "-A", help="Stage all changes (tracked + untracked)"),
    update: bool = typer.Option(False, "--update", "-u", help="Stage only tracked files with changes"),
    patch: bool = typer.Option(False, "--patch", "-p", help="Interactively stage hunks"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be staged"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    cwd = str(Path.cwd())
    args = ["add"]

    if dry_run:
        args.append("--dry-run")

    if patch:
        args.append("--patch")
    elif all:
        args.append("--all")
    elif update:
        args.append("--update")
    elif files:
        args.extend(files)
    else:
        print_error("Specify files or use --all / --update")
        raise typer.Exit(1)

    result = run_git(*args, cwd=cwd, check=False)

    if result.ok:
        if dry_run:
            if result.stdout.strip():
                console.print(result.stdout)
            else:
                print_info("Nothing to stage")
        else:
            if files:
                print_success(f"Staged: {', '.join(files)}")
            elif all:
                print_success("Staged all changes")
            elif update:
                print_success("Staged tracked file changes")
    else:
        if "did not match" in result.stderr:
            print_error(f"No files matched: {', '.join(files) if files else 'unknown'}")
        else:
            print_error(result.stderr)
        raise typer.Exit(1)
