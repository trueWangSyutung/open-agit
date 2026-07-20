"""Unified AI client using the openai library.

All AI calls go through OpenAI Chat Completions format.
All responses use JSON structured output.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agit.config.schema import AIConfig
from agit.i18n import t
from agit.utils.console import console, print_info, print_error
from agit.utils.errors import AIError


class AIClient:
    def __init__(self, config: AIConfig):
        self.config = config
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.config.apikey:
                print_error(t("ai.no_apikey"))
                raise AIError(t("ai.no_apikey"))
            self._client = OpenAI(
                api_key=self.config.apikey,
                base_url=self.config.baseurl,
                timeout=self.config.timeout,
            )
        return self._client

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and parse JSON response.

        All responses are returned as parsed JSON dicts.
        max_tokens is not sent — the model uses its default maximum.
        """
        model = model or self.config.model
        temp = temperature if temperature is not None else self.config.temperature

        console.print(
            f"[dim]→ {t('ai.sending', count=len(messages), tokens='auto', model=model, provider=self.config.provider)}[/dim]"
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except json.JSONDecodeError as e:
            raise AIError(f"AI returned invalid JSON: {e}")
        except Exception as e:
            if "timeout" in str(e).lower():
                raise AIError(t("ai.timeout", timeout=self.config.timeout))
            raise AIError(t("ai.error", error=str(e)))

    def chat_text(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        model: str | None = None,
    ) -> str:
        """Send a chat completion request and return plain text."""
        model = model or self.config.model
        temp = temperature if temperature is not None else self.config.temperature

        console.print(
            f"[dim]→ {t('ai.sending', count=len(messages), tokens='auto', model=model, provider=self.config.provider)}[/dim]"
        )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if "timeout" in str(e).lower():
                raise AIError(t("ai.timeout", timeout=self.config.timeout))
            raise AIError(t("ai.error", error=str(e)))

    def test_connection(self) -> tuple[bool, str]:
        """Test AI connectivity. Returns (ok, message)."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "Say 'ok' in JSON format: {\"status\": \"ok\"}"}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            json.loads(content)
            return True, t("config.ai_test_success", model=self.config.model)
        except Exception as e:
            return False, t("config.ai_test_failed", error=str(e))
