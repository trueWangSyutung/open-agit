"""Multi-source configuration loader with priority merging."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from agit.config.schema import AgitConfig

_DEFAULT_CONFIG = AgitConfig()


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_env() -> dict:
    mapping: dict[str, tuple[str, ...]] = {
        "AGIT_AI_BASEURL": ("ai", "baseurl"),
        "AGIT_AI_MODEL": ("ai", "model"),
        "AGIT_AI_APIKEY": ("ai", "apikey"),
        "AGIT_AI_PROVIDER": ("ai", "provider"),
        "AGIT_AI_TIMEOUT": ("ai", "timeout"),
        "AGIT_AI_TEMPERATURE": ("ai", "temperature"),
        "AGIT_AGENT_SOLO": ("agent", "solo"),
        "AGIT_AGENT_CONFIRM": ("agent", "confirm"),
        "AGIT_AGENT_DRY_RUN": ("agent", "dry_run"),
        "AGIT_AGENT_VERBOSE": ("agent", "verbose"),
    }
    result: dict = {}
    for env_key, path in mapping.items():
        val = os.environ.get(env_key)
        if val is not None:
            node = result
            for part in path[:-1]:
                node = node.setdefault(part, {})
            node[path[-1]] = _coerce(val)
    return result


def _coerce(val: str):
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def load_config(
    project_dir: Path | None = None,
    cli_overrides: dict | None = None,
) -> AgitConfig:
    """Load config with priority: CLI > env > project > user > defaults."""
    merged: dict = {}

    user_config = Path.home() / ".config" / "agit" / "config.toml"
    merged = _deep_merge(merged, _load_toml(user_config))

    if project_dir:
        project_config = project_dir / ".agit" / "config.toml"
        merged = _deep_merge(merged, _load_toml(project_config))

    merged = _deep_merge(merged, _load_env())

    if cli_overrides:
        merged = _deep_merge(merged, cli_overrides)

    return AgitConfig(**merged)


def get_config_source(key: str, project_dir: Path | None = None) -> str:
    """Determine which source a config key's value comes from."""
    env_key = f"AGIT_{key.upper().replace('.', '_')}"
    if os.environ.get(env_key):
        return "env"
    if project_dir:
        project_config = project_dir / ".agit" / "config.toml"
        if project_config.exists():
            data = _load_toml(project_config)
            parts = key.split(".")
            node = data
            for p in parts:
                if isinstance(node, dict) and p in node:
                    node = node[p]
                else:
                    node = None
                    break
            if node is not None:
                return "project"
    user_config = Path.home() / ".config" / "agit" / "config.toml"
    if user_config.exists():
        data = _load_toml(user_config)
        parts = key.split(".")
        node = data
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                node = None
                break
        if node is not None:
            return "user"
    return "default"
