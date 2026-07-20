"""Changelog prompt templates — all responses are JSON."""

CHANGELOG_SYSTEM = """You are a changelog generator. Output ONLY valid JSON.

Given a list of git commits, generate a structured changelog.
Group commits by type, rewrite technical descriptions for end users.
Identify breaking changes. Filter out noise (typo fixes, CI config).

Response format (JSON):
{
  "version": "string or null",
  "date": "YYYY-MM-DD",
  "sections": {
    "feat": [{"title": "user-readable description", "commits": ["sha1", "sha2"]}],
    "fix": [...],
    "perf": [...],
    "refactor": [...],
    "docs": [...],
    "chore": [...]
  },
  "breaking_changes": [
    {"title": "description", "commits": ["sha"]}
  ],
  "summary": "one paragraph summary of all changes"
}"""


def changelog_prompt(commits_text: str, locale: str = "zh-CN", repo_context: str = "") -> list[dict[str, str]]:
    lang = "Chinese" if "zh" in locale else "English"
    context_block = f"\n\nRepository Context:\n{repo_context}" if repo_context else ""
    return [
        {"role": "system", "content": CHANGELOG_SYSTEM},
        {
            "role": "user",
            "content": f"Generate a changelog in {lang} from these commits:{context_block}\n\n{commits_text}",
        },
    ]
