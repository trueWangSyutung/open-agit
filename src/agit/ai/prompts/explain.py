"""Explain prompt templates — uses free text with structured sections."""

EXPLAIN_SYSTEM = """You are a code change analyst. Output ONLY valid JSON.

Explain what changed in the given commits/diff in natural language.
Use the repository context to understand the project structure and affected areas.
Focus on: what changed, why it matters, potential impact, and risks.

Response format (JSON):
{
  "summary": "high-level summary of all changes",
  "changes": [
    {
      "area": "affected area/module",
      "description": "what changed and why",
      "impact": "potential impact on other parts"
    }
  ],
  "risks": ["list of potential risks or things to watch out for"],
  "per_commit": [
    {
      "sha": "short sha",
      "subject": "commit subject",
      "explanation": "what this commit does in plain language",
      "files_changed": ["list of key files"],
      "stats": "+additions/-deletions"
    }
  ]
}"""


def explain_prompt(diff_text: str, commit_info: str, locale: str = "zh-CN", repo_context: str = "") -> list[dict[str, str]]:
    lang = "Chinese" if "zh" in locale else "English"
    context_block = f"\n\nRepository Context:\n{repo_context}" if repo_context else ""
    return [
        {"role": "system", "content": EXPLAIN_SYSTEM},
        {
            "role": "user",
            "content": f"Explain these changes in {lang}:{context_block}\n\nCommit info:\n{commit_info}\n\nDiff:\n{diff_text}",
        },
    ]
