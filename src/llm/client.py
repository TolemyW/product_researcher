from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class ChatMessage:
    role: str
    content: str


class LLMClient:
    """Lightweight OpenAI-compatible chat completion client.

    Uses urllib from the standard library to avoid extra dependencies and keeps the
    surface small so it can be easily mocked in tests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.default_model = model
        self.timeout = timeout

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = 256,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM calls")

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._build_messages(prompt, system_prompt),
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset)
        parsed = json.loads(body)
        return self._extract_content(parsed)

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None) -> list[Dict[str, str]]:
        messages: list[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _extract_content(response: Dict[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response missing choices")
        message: Optional[Dict[str, Any]] = choices[0].get("message")
        if not message:
            raise RuntimeError("LLM response missing message content")
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("LLM content is not a string")
        return content.strip()


default_client = LLMClient()
