"""Thin, provider-agnostic LLM client.

Design goal: the agents never import `openai` or `httpx` directly. They call
`LLMClient.complete(...)`. Swapping providers is a config change, not a code
change — this matters for reproducibility (judges may run with their own key
against whichever provider you documented in the README).

Supported providers (set LLM_PROVIDER env var):
  - "openrouter" (default) — https://openrouter.ai, OpenAI-compatible API
  - "openai"                — api.openai.com directly

Both speak the OpenAI chat-completions wire format, so one HTTP client
handles both; only base_url + api_key + default model differ.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass
class LLMResponse:
    text: str
    raw: dict
    latency_seconds: float


class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.provider = provider or os.environ.get("LLM_PROVIDER", "openrouter")
        self.timeout = timeout

        if self.provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            self.model = model or os.environ.get(
                "LLM_MODEL", "anthropic/claude-3.5-sonnet"
            )
        elif self.provider == "openai":
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider}")

        if not self.api_key:
            raise RuntimeError(
                f"No API key found for provider={self.provider}. "
                f"Set {'OPENROUTER_API_KEY' if self.provider == 'openrouter' else 'OPENAI_API_KEY'}."
            )

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        json_mode: bool = False,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.base_url, headers=headers, json=payload)
        latency = time.monotonic() - start

        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(text=text, raw=data, latency_seconds=latency)

    @staticmethod
    def parse_json(text: str) -> dict:
        """Strip ```json fences if present and parse. Raises on failure —
        callers should treat a parse failure as an agent error, not silently
        swallow it (this matters for the accuracy metric)."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
