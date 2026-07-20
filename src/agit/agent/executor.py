"""Git command executor for agent — shows real output, auto-generates commit messages."""

from __future__ import annotations

import re
import shlex
import subprocess
import sys

from agit.utils.console import console, print_info, print_warning


class AgentExecutor:
    def __init__(self, cwd: str | None = None, ai_client=None, repo=None, config=None):
        self.cwd = cwd
        self.executed: list[dict] = []
        self.ai_client = ai_client
        self.repo = repo
        self.config = config

    def execute(self, command: str, dry_run: bool = False) -> tuple[bool, str]:
        """Execute a git command and show real output."""
        if not command.startswith("git"):
            print_info(f"Skipping non-git command: {command}")
            self.executed.append({"command": command, "result": "skipped", "output": ""})
            return True, ""

        command = self._fix_command(command)

        if self._is_bare_commit(command):
            command = self._auto_generate_commit_message()

        console.print(f"\n[bold]$ {command}[/bold]", highlight=False)
        sys.stdout.flush()

        try:
            parts = shlex.split(command)
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=60,
            )

            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode

        except subprocess.TimeoutExpired:
            console.print("[red]Command timed out[/red]")
            self.executed.append({
                "command": command, "result": "failed",
                "output": "", "error": "timeout",
            })
            return False, "timeout"
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            self.executed.append({
                "command": command, "result": "failed",
                "output": "", "error": str(e),
            })
            return False, str(e)

        if stdout:
            console.print(stdout.rstrip(), highlight=False)
        if stderr:
            if returncode == 0:
                console.print(f"[dim]{stderr.rstrip()}[/dim]", highlight=False)
            else:
                console.print(f"[red]{stderr.rstrip()}[/red]", highlight=False)

        sys.stdout.flush()

        if returncode == 0:
            self.executed.append({
                "command": command, "result": "success",
                "output": stdout, "error": stderr,
            })
            return True, stdout.strip()
        else:
            self.executed.append({
                "command": command, "result": "failed",
                "output": stdout, "error": stderr,
            })
            return False, stderr.strip()

    def _is_bare_commit(self, command: str) -> bool:
        """Check if command is a bare 'git commit' without -m flag."""
        if not re.match(r'git\s+commit\s*$', command):
            return False
        return True

    def _auto_generate_commit_message(self) -> str:
        """Auto-generate commit message using AI."""
        from agit.git.executor import run_git
        from agit.ai.sanitizer import sanitize_diff, truncate_diff

        print_info("Generating commit message...")

        name_result = run_git("diff", "--cached", "--name-only", cwd=self.cwd, check=False)
        staged_files = [f for f in name_result.stdout.strip().splitlines() if f]

        if not staged_files:
            status_result = run_git("status", "--porcelain", cwd=self.cwd, check=False)
            print_info(f"Working tree status:\n{status_result.stdout.strip()}")

            if status_result.stdout.strip():
                print_info("Found unstaged changes, running git add -A...")
                run_git("add", "-A", cwd=self.cwd, check=False)
                name_result = run_git("diff", "--cached", "--name-only", cwd=self.cwd, check=False)
                staged_files = [f for f in name_result.stdout.strip().splitlines() if f]

        if not staged_files:
            print_warning("No staged changes detected, using --allow-empty")
            return 'git commit --allow-empty -m "chore: empty commit"'

        print_info(f"Staged {len(staged_files)} files")

        diff_result = run_git("diff", "--cached", "--patch", cwd=self.cwd, check=False)
        diff_text = diff_result.stdout

        try:
            sanitized, _ = sanitize_diff(diff_text)
            truncated, _ = truncate_diff(sanitized)

            status = self.repo.get_status()
            head = run_git("rev-parse", "--short", "HEAD", cwd=self.cwd, check=False)
            head_sha = head.output if head.ok else "(no commits)"
            repo_context = f"Branch: {status.branch}\nHEAD: {head_sha}\nRemote: {status.remote_name} ({status.remote_url})"

            from agit.ai.prompts.commit import commit_prompt
            messages = commit_prompt(truncated, repo_context=repo_context)
            data = self.ai_client.chat_json(messages=messages, temperature=0.4)

            full_message = data.get("full_message", "")
            if not full_message:
                commit_type = data.get("type", "chore")
                scope = data.get("scope", "")
                subject = data.get("subject", "auto-generated commit")
                scope_str = f"({scope})" if scope else ""
                full_message = f"{commit_type}{scope_str}: {subject}"

            escaped = full_message.replace('"', '\\"')
            console.print(f"[dim]Message: {full_message}[/dim]")
            return f'git commit -m "{escaped}"'

        except Exception as e:
            print_warning(f"AI generation failed: {e}")
            return 'git commit -m "chore: auto commit"'

    def _fix_command(self, command: str) -> str:
        """Fix common AI-generated command issues."""
        cmd = command.strip()
        cmd = re.sub(r'\s+--dry-run\b', '', cmd)
        cmd = re.sub(r'(git\s+add)\s+\*', r'\1 -A', cmd)
        cmd = re.sub(r'\s+', ' ', cmd)
        return cmd

    def get_executed(self) -> list[dict]:
        return self.executed

    def get_last_output(self) -> str:
        if self.executed:
            return self.executed[-1].get("output", "")
        return ""
