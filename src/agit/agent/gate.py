"""Risk Gate — decision gate for agent execution."""

from __future__ import annotations

from agit.risk.classifier import RiskLevel, classify_command
from agit.risk.matrix import should_block
from agit.risk.context import assess_contextual_risk
from agit.config.schema import AgitConfig
from agit.git.repo import Repository
from agit.i18n import t
from agit.utils.console import console, Prompt


_DISCLAIMER = """
[red bold]⚠ 警告：此操作具有高风险[/red bold]

[dim]继续执行即表示您理解并接受以下条款：[/dim]
[red]• 此操作可能导致数据丢失或不可逆的仓库损坏[/red]
[red]• 执行后果由操作者自行承担，agit 不承担任何责任[/red]
[red]• 建议先备份重要数据或使用 --dry-run 预览[/red]
"""


_DISCLAIMER_EN = """
[red bold]⚠ WARNING: This operation is high-risk[/red bold]

[dim]By proceeding, you acknowledge and accept:[/dim]
[red]• This operation may cause data loss or irreversible repository damage[/red]
[red]• You bear full responsibility for the consequences[/red]
[red]• Consider backing up data or using --dry-run first[/red]
"""


class RiskGate:
    def __init__(self, config: AgitConfig, repo: Repository | None = None):
        self.config = config
        self.repo = repo

    def evaluate(self, steps: list[dict]) -> list[dict]:
        """Evaluate risk for all steps and annotate them."""
        evaluated = []
        status = self.repo.get_status() if self.repo else None

        for step in steps:
            cmd = step.get("command", "")
            base_risk = classify_command(cmd)

            if self.repo and status:
                risk = assess_contextual_risk(
                    cmd, base_risk, self.repo, status, self.config.risk
                )
            else:
                risk = base_risk

            step["risk"] = risk.value
            step["decision"] = self._get_decision(risk)
            evaluated.append(step)

        return evaluated

    def check_step(self, step: dict) -> tuple[bool, str]:
        """Check if a single step can proceed. Returns (can_proceed, reason)."""
        cmd = step.get("command", "")
        risk_str = step.get("risk", "LOW")
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            risk = RiskLevel.LOW

        blocked, reason = should_block(cmd, risk, self.config.agent.solo, self.config.risk)
        if blocked:
            return False, reason

        return True, ""

    def confirm_critical(self, command: str, locale: str = "zh_CN", context: dict | None = None) -> bool:
        """Ask for confirmation on blocked operations with disclaimer.

        Args:
            command: The git command to confirm
            locale: Language locale
            context: Optional dict with repo context (branch, remote, ahead, behind, etc.)

        Returns True if user confirms, False otherwise.
        """
        disclaimer = _DISCLAIMER if "zh" in locale else _DISCLAIMER_EN
        console.print(disclaimer)

        if context:
            console.print("[dim]--- Current Context ---[/dim]")
            if context.get("branch"):
                console.print(f"  Branch: [cyan]{context['branch']}[/cyan]")
            if context.get("remote"):
                console.print(f"  Remote: [cyan]{context['remote']}[/cyan] ({context.get('remote_url', '')})")
            if context.get("ahead") or context.get("behind"):
                console.print(f"  Status: ahead={context.get('ahead', 0)}, behind={context.get('behind', 0)}")
            if context.get("staged"):
                console.print(f"  Staged: {context['staged']} files")
            if context.get("head"):
                console.print(f"  HEAD: {context['head']}")
            console.print("[dim]-----------------------[/dim]")

        console.print(f"\n[bold]Command: [red]{command}[/red][/bold]\n")

        choice = Prompt.ask(
            "Type 'yes' to proceed",
            default="",
            show_choices=False,
        )

        if choice.lower() == "yes":
            return True

        console.print("[dim]Operation cancelled[/dim]")
        return False

    def _get_decision(self, risk: RiskLevel) -> str:
        if risk == RiskLevel.LOW:
            return "auto"
        if risk == RiskLevel.MEDIUM:
            return "auto" if self.config.agent.solo else "auto"
        if risk == RiskLevel.HIGH:
            return "auto" if self.config.agent.solo else "confirm"
        return "block"
