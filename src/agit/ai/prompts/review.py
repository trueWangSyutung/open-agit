"""Review prompt templates — all responses are JSON."""

REVIEW_SYSTEM = """You are a senior code reviewer. Output ONLY valid JSON.

Review the provided diff for: bugs, security issues, performance problems,
style violations, test coverage gaps, and dependency concerns.
Use the repository context to understand the project structure, conventions, and related files.

Response format (JSON):
{
  "issues": [
    {
      "severity": "critical|warning|suggestion",
      "file": "path/to/file.py",
      "line": 42,
      "category": "bug|security|performance|style|test|dependency",
      "title": "short title",
      "description": "what the issue is",
      "suggestion": "how to fix it (code if applicable)"
    }
  ],
  "good_practices": [
    {
      "file": "path/to/file.py",
      "description": "what was done well"
    }
  ],
  "summary": {
    "critical": 0,
    "warning": 0,
    "suggestion": 0,
    "overall": "one-line assessment"
  }
}"""


def review_prompt(diff_text: str, locale: str = "zh-CN", repo_context: str = "") -> list[dict[str, str]]:
    lang = "Chinese" if "zh" in locale else "English"
    context_block = f"\n\nRepository Context:\n{repo_context}" if repo_context else ""
    return [
        {"role": "system", "content": REVIEW_SYSTEM},
        {
            "role": "user",
            "content": f"Review this code. Write descriptions in {lang}:{context_block}\n\n{diff_text}",
        },
    ]
