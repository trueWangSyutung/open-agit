"""Unified error handling for agit."""

import sys
from agit.utils.console import error_console


class AgitError(Exception):
    """Base exception for agit."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ConfigError(AgitError):
    """Configuration related errors."""
    pass


class GitError(AgitError):
    """Git operation errors."""
    pass


class AIError(AgitError):
    """AI provider errors."""
    pass


class RiskBlockedError(AgitError):
    """Operation blocked by risk gate."""

    def __init__(self, message: str, command: str = ""):
        super().__init__(message, exit_code=2)
        self.command = command


class JournalError(AgitError):
    """Journal operation errors."""
    pass


def handle_error(e: Exception) -> None:
    """Handle an error and exit."""
    if isinstance(e, AgitError):
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)
    else:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)
