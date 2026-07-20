"""Configuration validator."""

from __future__ import annotations

from agit.config.schema import AgitConfig
from agit.i18n import t


class ValidationError:
    def __init__(self, key: str, message: str):
        self.key = key
        self.message = message

    def __str__(self) -> str:
        return f"{self.key}: {self.message}"


def validate_config(config: AgitConfig) -> list[ValidationError]:
    """Validate an AgitConfig and return list of errors."""
    errors: list[ValidationError] = []

    if config.ai.provider not in ("openai", "anthropic", "ollama", "custom", "azure"):
        errors.append(
            ValidationError("ai.provider", t("config.invalid", config_key="ai.provider",
                                              reason=f"unknown provider: {config.ai.provider}"))
        )

    if config.ai.timeout <= 0:
        errors.append(ValidationError("ai.timeout", "timeout must be positive"))

    if not 0 <= config.ai.temperature <= 2:
        errors.append(ValidationError("ai.temperature", "temperature must be 0-2"))

    if config.agent.confirm not in ("always", "never", "smart"):
        errors.append(ValidationError("agent.confirm", "must be always|never|smart"))

    if config.risk.force_push not in ("forbid", "confirm", "allow"):
        errors.append(ValidationError("risk.force_push", "must be forbid|confirm|allow"))

    for field in ("reset_hard", "delete_branch", "push_main", "clean"):
        val = getattr(config.risk, field)
        if val not in ("forbid", "confirm", "allow"):
            errors.append(ValidationError(f"risk.{field}", "must be forbid|confirm|allow"))

    return errors
