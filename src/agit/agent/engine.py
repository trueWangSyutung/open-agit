"""Agent engine — core execution loop with risk confirmation."""

from __future__ import annotations

import time
from typing import Any

from agit.ai.client import AIClient
from agit.agent.planner import generate_plan
from agit.agent.gate import RiskGate
from agit.agent.executor import AgentExecutor
from agit.agent.presenter import present_plan, present_risk_summary, present_step_result
from agit.config.schema import AgitConfig
from agit.git.repo import Repository
from agit.journal.writer import JournalWriter
from agit.journal.snapshot import SnapshotManager
from agit.i18n import t
from agit.utils.console import console, print_info, print_warning, print_error, Prompt


class AgentEngine:
    def __init__(
        self,
        config: AgitConfig,
        ai_client: AIClient,
        repo: Repository,
        cwd: str | None = None,
    ):
        self.config = config
        self.ai_client = ai_client
        self.repo = repo
        self.cwd = cwd or str(repo.path)
        self.gate = RiskGate(config, repo)
        self.executor = AgentExecutor(self.cwd, ai_client=ai_client, repo=repo, config=config)
        agit_dir = repo.path / ".agit"
        self.journal = JournalWriter(agit_dir)
        self.snapshot = SnapshotManager(agit_dir)

    def _get_context(self) -> dict:
        """Get current repository context for confirmation dialogs."""
        status = self.repo.get_status()
        return {
            "branch": status.branch,
            "remote": status.remote_name,
            "remote_url": status.remote_url,
            "ahead": status.ahead,
            "behind": status.behind,
            "staged": len(status.staged_files),
            "head": self.repo.get_head_sha(short=True),
            "dirty": status.is_dirty,
            "conflicts": status.has_conflicts,
        }

    def run(self, intent: str, dry_run: bool | None = None) -> dict[str, Any]:
        """Run an agent session. Returns the journal session dict."""
        if dry_run is None:
            dry_run = self.config.agent.dry_run

        start_time = time.time()

        console.print(f"\n[bold]{t('agent.start')}[/bold]")
        print_info(f"Intent: {intent}")

        snapshot_dir = self.snapshot.create_snapshot(cwd=self.cwd)
        print_info(t("journal.snapshot_created", path=str(snapshot_dir)))

        session = self.journal.create_session(
            trigger="agit agent",
            intent=intent,
            mode="solo" if self.config.agent.solo else "interactive",
        )
        session["snapshot_before"] = str(snapshot_dir)
        session["ai_model"] = self.config.ai.model

        plan_data = generate_plan(self.ai_client, self.config, intent, self.repo)
        steps = plan_data.get("steps", [])

        if not steps:
            print_warning("No steps generated from intent")
            return session

        steps = self.gate.evaluate(steps)

        decision = self._get_user_decision(steps, dry_run)

        if decision == "abort":
            print_warning(t("plan.aborted"))
            return session
        elif decision == "reject":
            print_info(t("plan.rejected"))
            return session
        elif decision == "approve":
            self._execute_plan(steps, session, dry_run)
        elif decision == "edit":
            self._step_by_step(steps, session, dry_run)

        duration_ms = int((time.time() - start_time) * 1000)
        session["duration_ms"] = duration_ms

        filepath = self.journal.save_session(session)
        print_info(t("journal.written", path=str(filepath)))

        console.print(f"[bold green]{t('agent.done')}[/bold green]")
        return session

    def _get_user_decision(self, steps: list[dict], dry_run: bool) -> str:
        if self.config.agent.solo and not dry_run:
            return "approve"

        present_plan(steps, dry_run=dry_run)
        present_risk_summary(steps)
        console.print()

        choice = Prompt.ask(
            t("plan.approve"),
            choices=["y", "N", "e", "a"],
            default="N",
            show_choices=True,
        )

        mapping = {"y": "approve", "N": "reject", "e": "edit", "a": "abort"}
        return mapping.get(choice, "reject")

    def _execute_plan(self, steps: list[dict], session: dict, dry_run: bool) -> None:
        print_info(t("plan.approved"))
        max_steps = self.config.agent.max_steps
        locale = self.config.changelog.locale
        context = self._get_context()

        for i, step in enumerate(steps):
            if i >= max_steps:
                print_warning(t("agent.max_steps", max_steps=max_steps))
                break

            can_proceed, reason = self.gate.check_step(step)
            if not can_proceed:
                cmd = step.get("command", "")
                risk = step.get("risk", "LOW")

                console.print(f"\n[red bold]BLOCKED ({risk}): {cmd}[/red bold]")
                confirmed = self.gate.confirm_critical(cmd, locale=locale, context=context)
                if confirmed:
                    success, output = self.executor.execute(cmd)
                    result = "success" if success else "failed"
                    present_step_result(step, result)
                    self.journal.add_step(
                        session, command=cmd, risk=risk,
                        decision="user_confirmed", result=result,
                    )
                else:
                    self.journal.add_step(
                        session, command=cmd, risk=risk,
                        decision="user_declined", result="skipped",
                    )
                continue

            if dry_run:
                present_step_result(step, "dry-run")
                self.journal.add_step(
                    session, command=step.get("command", ""),
                    risk=step.get("risk", "LOW"),
                    decision="dry-run", result="dry-run",
                )
                continue

            success, output = self.executor.execute(step.get("command", ""))
            result = "success" if success else "failed"
            present_step_result(step, result)

            commit_hash = None
            if success and "commit" in step.get("command", ""):
                commit_hash = self.executor.get_last_output().split()[-1] if self.executor.get_last_output() else None

            self.journal.add_step(
                session, command=step.get("command", ""),
                risk=step.get("risk", "LOW"),
                decision=step.get("decision", "auto"),
                result=result, commit_hash=commit_hash,
            )

    def _step_by_step(self, steps: list[dict], session: dict, dry_run: bool) -> None:
        print_info(t("plan.step_by_step"))
        locale = self.config.changelog.locale
        context = self._get_context()

        for step in steps:
            console.print(f"\n[bold]{t('agent.step', current=step.get('id', '?'), total=len(steps))}[/bold]")
            console.print(f"  {step.get('command', '')}")
            if step.get("description"):
                console.print(f"  [dim]{step['description']}[/dim]")
            console.print(f"  Risk: [{step.get('risk', 'LOW')}]")

            choice = Prompt.ask(
                "Execute?",
                choices=["y", "n", "s"],
                default="y",
                show_choices=True,
            )

            if choice == "y":
                can_proceed, reason = self.gate.check_step(step)
                if not can_proceed:
                    cmd = step.get("command", "")
                    risk = step.get("risk", "LOW")

                    console.print(f"\n[red bold]BLOCKED ({risk}): {cmd}[/red bold]")
                    confirmed = self.gate.confirm_critical(cmd, locale=locale, context=context)
                    if confirmed:
                        success, _ = self.executor.execute(cmd)
                        result = "success" if success else "failed"
                        present_step_result(step, result)
                        self.journal.add_step(
                            session, command=cmd, risk=risk,
                            decision="user_confirmed", result=result,
                        )
                    else:
                        self.journal.add_step(
                            session, command=cmd, risk=risk,
                            decision="user_declined", result="skipped",
                        )
                    continue

                if dry_run:
                    present_step_result(step, "dry-run")
                    self.journal.add_step(
                        session, command=step.get("command", ""),
                        risk=step.get("risk", "LOW"),
                        decision="dry-run", result="dry-run",
                    )
                else:
                    success, _ = self.executor.execute(step.get("command", ""))
                    result = "success" if success else "failed"
                    present_step_result(step, result)
                    self.journal.add_step(
                        session, command=step.get("command", ""),
                        risk=step.get("risk", "LOW"),
                        decision="approved_by_user", result=result,
                    )
            elif choice == "n":
                self.journal.add_step(
                    session, command=step.get("command", ""),
                    risk=step.get("risk", "LOW"),
                    decision="skipped_by_user", result="skipped",
                )
            else:
                break
