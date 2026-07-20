"""agit init — initialize .agit/ directory and git repo."""

from __future__ import annotations

from pathlib import Path

import typer

from agit.git.executor import run_git
from agit.i18n import t
from agit.utils.console import console, print_success, print_warning, print_info

app = typer.Typer(help="Initialize agit in the current repository")


@app.callback(invoke_without_command=True)
def init_cmd(
    ctx: typer.Context,
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    cwd = Path.cwd()

    git_dir = cwd / ".git"
    if not git_dir.exists():
        print_info("Initializing git repository...")
        run_git("init", cwd=str(cwd))
        print_success("Git repository initialized")

    agit_dir = cwd / ".agit"

    if agit_dir.exists():
        print_warning(t("init.already_exists"))
        return

    print_info(t("init.start"))

    agit_dir.mkdir(parents=True)
    (agit_dir / "history").mkdir()
    (agit_dir / "snapshots").mkdir()

    config_path = agit_dir / "config.toml"
    config_path.write_text(_generate_default_toml())

    gitignore = cwd / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""

    ignore_block = _generate_gitignore_block()
    missing = []
    for line in ignore_block.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in existing:
            missing.append(line)

    if missing:
        separator = "\n" if existing and not existing.endswith("\n") else ""
        new_content = existing.rstrip() + separator + "\n".join(missing) + "\n"
        gitignore.write_text(new_content)
        print_info(f"Updated .gitignore (+{len(missing)} entries)")
    elif not gitignore.exists():
        gitignore.write_text(ignore_block)
        print_info(f"Created .gitignore")

    print_success(t("init.done"))
    print_info(t("init.created_config", path=str(config_path)))
    print_info("Tip: set AGIT_AI_APIKEY env var to avoid storing keys in config")


def _generate_gitignore_block() -> str:
    return """
# === agit ===
.agit/snapshots/
.agit/history/

# === AI/IDE ===
.mimocode/
.claude/
.cursor/
.vscode/
.idea/

# === OS ===
.DS_Store
Thumbs.db
Desktop.ini

# === Python ===
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg
.eggs/
*.whl

# === Env ===
.env
.env.*
!.env.example

# === Logs ===
*.log
logs/

# === Secrets ===
*.pem
*.key
*.cert
id_rsa*
*.jks

# === Node ===
node_modules/
npm-debug.log*

# === Misc ===
*.tmp
*.bak
*.swp
*~
"""


def _generate_default_toml() -> str:
    return """# agit configuration
# AI provider settings — prefer env vars: AGIT_AI_APIKEY, AGIT_AI_BASEURL, AGIT_AI_MODEL

[ai]
baseurl    = "https://api.openai.com/v1"
model      = "gpt-4o"
apikey     = ""
provider   = "openai"
timeout    = 30
temperature = 0.3

[agent]
solo       = false
confirm    = "smart"
dry_run    = true
verbose    = false
max_steps  = 20
auto_push  = false

[risk]
force_push       = "forbid"
reset_hard       = "confirm"
delete_branch    = "confirm"
push_main        = "confirm"
clean            = "confirm"
protected_branches = ["main", "master", "release/*"]

[changelog]
conventional = true
sections     = ["feat", "fix", "perf", "refactor", "docs", "chore"]
locale       = "zh-CN"

[commit]
conventional    = true
auto_stage      = false
signoff         = false
scope_inference = true

[doctor]
max_file_size    = "50MB"
binary_extensions = [".exe", ".dll", ".so", ".dylib", ".bin"]
"""
