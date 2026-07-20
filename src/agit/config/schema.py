"""Configuration schema using Pydantic."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    baseurl: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    apikey: str = ""
    provider: str = "openai"
    timeout: int = 30
    temperature: float = 0.3


class AgentConfig(BaseModel):
    solo: bool = False
    confirm: str = "smart"
    dry_run: bool = True
    verbose: bool = False
    max_steps: int = 20
    auto_push: bool = False


class RiskConfig(BaseModel):
    force_push: str = "forbid"
    reset_hard: str = "confirm"
    delete_branch: str = "confirm"
    push_main: str = "confirm"
    clean: str = "confirm"
    protected_branches: list[str] = Field(
        default_factory=lambda: ["main", "master", "release/*"]
    )


class ChangelogConfig(BaseModel):
    conventional: bool = True
    sections: list[str] = Field(
        default_factory=lambda: ["feat", "fix", "perf", "refactor", "docs", "chore"]
    )
    locale: str = "zh-CN"


class CommitConfig(BaseModel):
    conventional: bool = True
    auto_stage: bool = False
    signoff: bool = False
    scope_inference: bool = True


class DoctorConfig(BaseModel):
    sensitive_patterns: list[str] = Field(
        default_factory=lambda: [
            r"AKIA[0-9A-Z]{16}",
            r"sk-[a-zA-Z0-9]{48}",
            r"ghp_[a-zA-Z0-9]{36}",
        ]
    )
    max_file_size: str = "50MB"
    binary_extensions: list[str] = Field(
        default_factory=lambda: [".exe", ".dll", ".so", ".dylib", ".bin"]
    )


class AgitConfig(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    changelog: ChangelogConfig = Field(default_factory=ChangelogConfig)
    commit: CommitConfig = Field(default_factory=CommitConfig)
    doctor: DoctorConfig = Field(default_factory=DoctorConfig)
