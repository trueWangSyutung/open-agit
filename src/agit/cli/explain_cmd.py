"""agit explain — commit explanation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.markdown import Markdown

from agit.ai.client import AIClient
from agit.config.loader import load_config
from agit.features.explain import explain_commits, explain_single_commit
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_error

app = typer.Typer(help="Explain commits in natural language")


@app.callback(invoke_without_command=True)
def explain_cmd(
    ctx: typer.Context,
    ref: str = typer.Argument("HEAD", help="Commit or range to explain"),
    file: str = typer.Option(None, "--file", help="Explain changes to a specific file"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    config = load_config(project_dir=Path.cwd())
    client = AIClient(config.ai)
    repo = Repository(Path.cwd())

    print_info(t("explain.generating"))

    if ".." in ref:
        from_ref, to_ref = ref.split("..", 1)
        data = explain_commits(config, client, repo, from_ref=from_ref, to_ref=to_ref)
    elif ref in ("HEAD", "HEAD~0"):
        data = explain_single_commit(config, client, repo, "HEAD")
    else:
        data = explain_single_commit(config, client, repo, ref)

    if "error" in data:
        print_error(data["error"])
        raise typer.Exit(1)

    _display_explain(data)


def _display_explain(data: dict) -> None:
    lines = []

    if data.get("range"):
        lines.append(f"**Range:** {data['range']}")
    if data.get("commit_count"):
        lines.append(f"**Commits:** {data['commit_count']}")
    lines.append("")

    if data.get("summary"):
        lines.append(f"## Summary\n\n{data['summary']}\n")

    if data.get("changes"):
        lines.append("## Changes\n")
        for change in data["changes"]:
            lines.append(f"### {change.get('area', 'Unknown')}\n")
            lines.append(f"{change.get('description', '')}\n")
            if change.get("impact"):
                lines.append(f"**Impact:** {change['impact']}\n")

    if data.get("risks"):
        lines.append("## Risks\n")
        for risk in data["risks"]:
            lines.append(f"- {risk}")
        lines.append("")

    if data.get("per_commit"):
        lines.append("## Per-Commit Breakdown\n")
        for c in data["per_commit"]:
            lines.append(f"### `{c.get('sha', '')}` {c.get('subject', '')}\n")
            lines.append(f"{c.get('explanation', '')}\n")
            if c.get("files_changed"):
                lines.append(f"Files: {', '.join(c['files_changed'])}\n")

    md = "\n".join(lines)
    console.print(Panel(Markdown(md), title=t("explain.title"), border_style="blue"))
