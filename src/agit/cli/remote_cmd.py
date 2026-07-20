"""agit remote — manage remote repositories."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from agit.git.executor import run_git
from agit.i18n import t
from agit.utils.console import console, print_success, print_error, print_info, print_warning, Prompt

app = typer.Typer(help="Manage remote repositories")


@app.command("add")
def remote_add(
    url: str = typer.Argument(help="Remote URL (GitHub/Gitee/GitLab)"),
    name: str = typer.Option(None, "--name", "-n", help="Remote name (auto-detected if not set)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing remote"),
) -> None:
    """Add a remote repository from URL."""
    if name is None:
        name = _guess_name(url)

    console.print(f"[dim]URL: {url}[/dim]")
    console.print(f"[dim]Name: {name}[/dim]")

    existing = _get_remote_url(name)
    if existing:
        if force:
            print_warning(f"Remote '{name}' already exists ({existing}), overwriting")
            run_git("remote", "remove", name, cwd=str(Path.cwd()), check=False)
        else:
            print_error(f"Remote '{name}' already exists: {existing}")
            print_info(f"Use --force to overwrite, or --name to use a different name")
            raise typer.Exit(1)

    result = run_git("remote", "add", name, url, cwd=str(Path.cwd()), check=False)
    if result.ok:
        print_success(f"Remote '{name}' added: {url}")

        if _is_ssh_url(url):
            print_info("Using SSH URL — make sure your SSH key is configured")
        else:
            print_info("Using HTTPS URL — you may need to authenticate on push")
    else:
        print_error(f"Failed to add remote: {result.stderr}")
        raise typer.Exit(1)


@app.command("list")
@app.command("ls")
def remote_list() -> None:
    """List all remotes."""
    result = run_git("remote", "-v", cwd=str(Path.cwd()), check=False)
    if not result.ok or not result.output:
        print_info("No remotes configured")
        return

    table = Table(title="Remotes", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("URL")
    table.add_column("Type", style="dim")

    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            url = parts[1]
            fetch_push = parts[2].strip("()")
            url_type = "SSH" if _is_ssh_url(url) else "HTTPS"
            table.add_row(name, url, f"{fetch_push} ({url_type})")

    console.print(table)


@app.command("remove")
@app.command("rm")
def remote_remove(
    name: str = typer.Argument(help="Remote name to remove"),
) -> None:
    """Remove a remote repository."""
    existing = _get_remote_url(name)
    if not existing:
        print_error(f"Remote '{name}' not found")
        raise typer.Exit(1)

    result = run_git("remote", "remove", name, cwd=str(Path.cwd()), check=False)
    if result.ok:
        print_success(f"Remote '{name}' removed")
    else:
        print_error(f"Failed to remove remote: {result.stderr}")


@app.command("set-url")
def remote_set_url(
    name: str = typer.Argument(help="Remote name"),
    url: str = typer.Argument(help="New URL"),
) -> None:
    """Change the URL of a remote."""
    result = run_git("remote", "set-url", name, url, cwd=str(Path.cwd()), check=False)
    if result.ok:
        print_success(f"Remote '{name}' URL updated: {url}")
    else:
        print_error(f"Failed to update URL: {result.stderr}")


@app.command("rename")
def remote_rename(
    old_name: str = typer.Argument(help="Current remote name"),
    new_name: str = typer.Argument(help="New remote name"),
) -> None:
    """Rename a remote."""
    result = run_git("remote", "rename", old_name, new_name, cwd=str(Path.cwd()), check=False)
    if result.ok:
        print_success(f"Remote renamed: {old_name} → {new_name}")
    else:
        print_error(f"Failed to rename: {result.stderr}")


@app.command("setup")
def remote_setup(
    url: str = typer.Argument(help="Repository URL (GitHub/Gitee/GitLab)"),
    name: str = typer.Option(None, "--name", "-n", help="Remote name"),
    default_branch: str = typer.Option("main", "--branch", "-b", help="Default branch name"),
    push: bool = typer.Option(False, "--push", "-p", help="Push current branch after setup"),
) -> None:
    """Full remote setup: add remote + push branch."""
    if name is None:
        name = _guess_name(url)

    existing = _get_remote_url(name)
    if existing:
        print_warning(f"Remote '{name}' already exists: {existing}")
        choice = Prompt.ask("Overwrite?", choices=["y", "N"], default="N")
        if choice != "y":
            print_info("Cancelled")
            return
        run_git("remote", "remove", name, cwd=str(Path.cwd()), check=False)

    result = run_git("remote", "add", name, url, cwd=str(Path.cwd()), check=False)
    if not result.ok:
        print_error(f"Failed to add remote: {result.stderr}")
        raise typer.Exit(1)

    print_success(f"Remote '{name}' added: {url}")

    current_branch = run_git("branch", "--show-current", cwd=str(Path.cwd()), check=False).output
    if not current_branch:
        current_branch = default_branch

    if push:
        print_info(f"Pushing to {name}/{current_branch}...")
        push_result = run_git("push", "-u", name, current_branch, cwd=str(Path.cwd()), check=False)
        if push_result.ok:
            print_success(f"Pushed to {name}/{current_branch}")
        else:
            print_error(f"Push failed: {push_result.stderr}")
            print_info("You may need to authenticate first")
    else:
        print_info(f"To push: git push -u {name} {current_branch}")


def _guess_name(url: str) -> str:
    """Guess remote name from URL."""
    url_lower = url.lower()
    if "github.com" in url_lower:
        return "github"
    elif "gitee.com" in url_lower:
        return "gitee"
    elif "gitlab.com" in url_lower:
        return "gitlab"
    elif "bitbucket.org" in url_lower:
        return "bitbucket"
    else:
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            return parts[-1].replace(".git", "")
        return "origin"


def _is_ssh_url(url: str) -> bool:
    return url.startswith("git@") or url.startswith("ssh://")


def _get_remote_url(name: str) -> str | None:
    result = run_git("remote", "get-url", name, cwd=str(Path.cwd()), check=False)
    return result.output if result.ok and result.output else None
