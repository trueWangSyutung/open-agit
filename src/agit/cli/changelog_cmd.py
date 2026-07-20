"""agit changelog — AI-generated changelog."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from agit.ai.client import AIClient
from agit.config.loader import load_config
from agit.features.changelog import generate_changelog, format_changelog_markdown, format_changelog_json
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_success, print_error

app = typer.Typer(help="AI-generated changelog from git history")


@app.callback(invoke_without_command=True)
def changelog_cmd(
    ctx: typer.Context,
    from_ref: str = typer.Option(None, "--from", help="Start ref (tag/commit)"),
    to_ref: str = typer.Option("HEAD", "--to", help="End ref"),
    output: str = typer.Option(None, "--output", "-o", help="Write to file"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown|json"),
    preview: bool = typer.Option(True, "--preview/--no-preview", help="Preview only"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    config = load_config(project_dir=Path.cwd())
    client = AIClient(config.ai)
    repo = Repository(Path.cwd())

    print_info(t("changelog.generating"))
    data = generate_changelog(config, client, repo, from_ref=from_ref, to_ref=to_ref)

    if "error" in data:
        print_error(data["error"])
        raise typer.Exit(1)

    if format == "json":
        result = format_changelog_json(data)
    else:
        result = format_changelog_markdown(data, config.changelog.sections)

    if output and not preview:
        Path(output).write_text(result, encoding="utf-8")
        print_success(t("changelog.written", path=output))
    else:
        console.print(Panel(Markdown(result), title=t("changelog.preview"), border_style="blue"))
