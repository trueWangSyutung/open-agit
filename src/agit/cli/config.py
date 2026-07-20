"""agit config — view/modify configuration."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from agit.config.loader import load_config, get_config_source, _load_toml
from agit.config.validator import validate_config
from agit.config.schema import AgitConfig
from agit.i18n import t
from agit.utils.console import console, print_success, print_warning, print_error, print_info

app = typer.Typer(help="View/modify agit configuration")


@app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g. ai.model)"),
    value: str = typer.Argument(help="Config value"),
    project: bool = typer.Option(False, "--project", "-p", help="Write to project config (.agit/config.toml)"),
) -> None:
    """Set a configuration value.

    Default: writes to ~/.config/agit/config.toml (system-wide).
    Use --project to write to .agit/config.toml (project-only).
    """
    parts = key.split(".")
    if len(parts) != 2:
        print_error("Key must be in format: section.key (e.g. ai.model)")
        raise typer.Exit(1)

    section, field = parts

    if project:
        config_path = Path.cwd() / ".agit" / "config.toml"
        if not config_path.exists():
            print_error("Run 'agit init' first")
            raise typer.Exit(1)
        scope = "project"
    else:
        config_path = Path.home() / ".config" / "agit" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            config_path.write_text("# agit system-wide configuration\n")
        scope = "system"

    if key == "ai.apikey" and not value.startswith("$"):
        print_warning("Consider using AGIT_AI_APIKEY environment variable instead")
        print_info("  export AGIT_AI_APIKEY='your-key-here'")

    try:
        _update_toml(config_path, section, field, value)
        print_success(f"[{scope}] {key} = {value}")
    except Exception as e:
        print_error(f"Failed to update config: {e}")
        raise typer.Exit(1)


@app.command("get")
def config_get(
    key: str = typer.Argument(help="Config key"),
) -> None:
    """Get a configuration value."""
    config = load_config(project_dir=Path.cwd())
    parts = key.split(".")
    if len(parts) != 2:
        print_error("Key must be in format: section.key")
        raise typer.Exit(1)

    section, field = parts
    section_obj = getattr(config, section, None)
    if section_obj is None:
        print_error(t("config.not_found", config_key=key))
        raise typer.Exit(1)

    value = getattr(section_obj, field, None)
    if value is None:
        print_error(t("config.not_found", config_key=key))
        raise typer.Exit(1)

    source = get_config_source(key, project_dir=Path.cwd())
    console.print(f"{key} = {value}  [dim]({source})[/dim]")


@app.command("list")
def config_list() -> None:
    """List all configuration values."""
    config = load_config(project_dir=Path.cwd())

    table = Table(title=t("config.list_title"), show_header=True, header_style="bold")
    table.add_column(t("config.key"), style="cyan")
    table.add_column(t("config.value"))
    table.add_column(t("config.source"), style="dim")

    for section_name in ["ai", "agent", "risk", "changelog", "commit", "doctor"]:
        section = getattr(config, section_name)
        for field_name, field_info in section.model_fields.items():
            key = f"{section_name}.{field_name}"
            value = getattr(section, field_name)
            source = get_config_source(key, project_dir=Path.cwd())
            table.add_row(key, str(value), source)

    console.print(table)


@app.command("validate")
def config_validate() -> None:
    """Validate configuration and test AI connectivity."""
    print_info(t("config.validating"))
    config = load_config(project_dir=Path.cwd())

    errors = validate_config(config)
    if errors:
        for err in errors:
            print_error(str(err))
        raise typer.Exit(1)

    print_success(t("config.valid"))

    if config.ai.apikey:
        from agit.ai.client import AIClient
        client = AIClient(config.ai)
        ok, msg = client.test_connection()
        if ok:
            print_success(msg)
        else:
            print_error(msg)
    else:
        print_warning(t("ai.no_apikey"))


@app.command("reset")
def config_reset(
    project: bool = typer.Option(False, "--project", "-p", help="Reset project config"),
) -> None:
    """Reset configuration to defaults."""
    if project:
        config_path = Path.cwd() / ".agit" / "config.toml"
        scope = "project"
    else:
        config_path = Path.home() / ".config" / "agit" / "config.toml"
        scope = "system"

    if config_path.exists():
        config_path.unlink()
    print_success(f"[{scope}] {t('config.reset')}")


def _update_toml(path: Path, section: str, field: str, value: str) -> None:
    content = path.read_text()
    lines = content.splitlines()

    in_section = False
    updated = False
    new_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped == f"[{section}]":
            in_section = True
            new_lines.append(line)
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not updated:
                new_lines.append(f'{field} = "{value}"')
                updated = True
            in_section = False
            new_lines.append(line)
            continue

        if in_section:
            uncommented = stripped.lstrip("# ").strip()
            if uncommented.startswith(f"{field} ") or uncommented.startswith(f"{field}="):
                new_lines.append(f'{field} = "{value}"')
                updated = True
                continue

        new_lines.append(line)

    if in_section and not updated:
        new_lines.append(f'{field} = "{value}"')
        updated = True

    if not updated:
        new_lines.append(f"\n[{section}]")
        new_lines.append(f'{field} = "{value}"')

    path.write_text("\n".join(new_lines) + "\n")
