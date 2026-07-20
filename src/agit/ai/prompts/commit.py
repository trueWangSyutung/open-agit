"""Commit message prompt templates — all responses are JSON."""

COMMIT_SYSTEM = """You are a commit message generator. Output ONLY valid JSON.

Analyze the provided git diff and generate a conventional commit message.
Use the repository context to infer the correct scope (e.g., the module or component being changed).

Response format (JSON):
{
  "type": "feat|fix|perf|refactor|docs|chore|style|test|build|ci",
  "scope": "component name or empty string",
  "subject": "imperative mood, lowercase, no period, max 72 chars",
  "body": "detailed explanation of what and why (can be empty)",
  "footer": "Closes #123, BREAKING CHANGE: etc (can be empty)",
  "full_message": "the complete formatted commit message"
}"""


COMMIT_SYSTEM_AMEND = """You are a commit message editor. Output ONLY valid JSON.

Given the current commit message and new changes, generate an updated commit message.

Response format (JSON):
{
  "type": "feat|fix|perf|refactor|docs|chore|style|test|build|ci",
  "scope": "component name or empty string",
  "subject": "imperative mood, lowercase, no period, max 72 chars",
  "body": "detailed explanation (can be empty)",
  "footer": "footers (can be empty)",
  "full_message": "the complete formatted commit message"
}"""


def commit_prompt(diff_text: str, repo_context: str = "") -> list[dict[str, str]]:
    context_block = f"\n\nRepository Context:\n{repo_context}" if repo_context else ""
    return [
        {"role": "system", "content": COMMIT_SYSTEM},
        {
            "role": "user",
            "content": f"Generate a commit message for this diff:{context_block}\n\n{diff_text}",
        },
    ]


def commit_amend_prompt(diff_text: str, current_message: str, repo_context: str = "") -> list[dict[str, str]]:
    context_block = f"\n\nRepository Context:\n{repo_context}" if repo_context else ""
    return [
        {"role": "system", "content": COMMIT_SYSTEM_AMEND},
        {
            "role": "user",
            "content": f"Current message:\n{current_message}\n\nNew diff:{context_block}\n\n{diff_text}",
        },
    ]
