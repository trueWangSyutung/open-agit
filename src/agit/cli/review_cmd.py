"""agit review — AI code review."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.ai.client import AIClient
from agit.config.loader import load_config
from agit.features.review import review_staged, review_all, review_commit, review_range
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, print_info, print_error, Prompt

app = typer.Typer(help="AI-powered code review")


@app.callback(invoke_without_command=True)
def review_cmd(
    ctx: typer.Context,
    all: bool = typer.Option(False, "--all", "-a", help="Review all changes"),
    range_opt: str = typer.Option(None, "--range", help="Review range (from..to)"),
    ref: str = typer.Argument(None, help="Commit ref to review"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    config = load_config(project_dir=Path.cwd())
    client = AIClient(config.ai)
    repo = Repository(Path.cwd())

    print_info(t("review.analyzing"))

    if range_opt:
        from_ref, to_ref = range_opt.split("..", 1)
        data = review_range(config, client, repo, from_ref, to_ref)
    elif ref:
        data = review_commit(config, client, repo, ref)
    elif all:
        data = review_all(config, client, repo)
    else:
        data = review_staged(config, client, repo)

    if "_diff_summary" in data:
        summary_parts = data["_diff_summary"]
        add_count = summary_parts.split("+")[1].split("/")[0] if "+" in summary_parts else "?"
        del_count = summary_parts.split("-")[1].split(" ")[0] if "-" in summary_parts else "?"
        msg = t("review.staged", **{"files": data["_file_count"], "add": add_count, "del": del_count})
        print_info(msg)

    _display_review(data, config)


def _display_review(data: dict, config) -> None:
    issues = data.get("issues", [])
    good = data.get("good_practices", [])
    summary = data.get("summary", {})

    severity_groups = {"critical": [], "warning": [], "suggestion": []}
    for issue in issues:
        sev = issue.get("severity", "suggestion")
        severity_groups.setdefault(sev, []).append(issue)

    if severity_groups["critical"]:
        console.print(f"\n[red bold]{t('review.critical')} ({len(severity_groups['critical'])})[/red bold]")
        console.print("─" * 40)
        for issue in severity_groups["critical"]:
            _print_issue(issue, "red")

    if severity_groups["warning"]:
        console.print(f"\n[yellow bold]{t('review.warning')} ({len(severity_groups['warning'])})[/yellow bold]")
        console.print("─" * 40)
        for issue in severity_groups["warning"]:
            _print_issue(issue, "yellow")

    if severity_groups["suggestion"]:
        console.print(f"\n[blue]{t('review.suggestion')} ({len(severity_groups['suggestion'])})[/blue]")
        console.print("─" * 40)
        for issue in severity_groups["suggestion"]:
            _print_issue(issue, "blue")

    if good:
        console.print(f"\n[green]{t('review.good')}[/green]")
        console.print("─" * 40)
        for g in good:
            console.print(f"  [green]✓[/green] {g.get('file', '')}: {g.get('description', '')}")

    summary_text = t("review.summary",
        critical=summary.get('critical', 0),
        warning=summary.get('warning', 0),
        suggestion=summary.get('suggestion', 0))
    console.print(f"\n[bold]{summary_text}[/bold]")

    if summary.get("overall"):
        console.print(f"[dim]{summary['overall']}[/dim]")

    if severity_groups["critical"]:
        choice = Prompt.ask(
            "Action",
            choices=["f", "c", "q"],
            default="q",
            show_choices=True,
        )
        if choice == "f":
            print_info("Auto-fix not yet implemented")
        elif choice == "c":
            print_info("Continuing with commit...")


def _print_issue(issue: dict, color: str) -> None:
    file_loc = issue.get("file", "")
    line = issue.get("line", "")
    loc = f"{file_loc}:{line}" if line else file_loc
    console.print(f"\n  [{color}]{loc}[/{color}]  {issue.get('title', '')}")
    console.print(f"    {issue.get('description', '')}")
    if issue.get("suggestion"):
        console.print(f"    → {issue['suggestion']}")
