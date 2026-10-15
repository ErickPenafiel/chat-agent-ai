"""Groq vía su endpoint compatible con OpenAI (chat completions)."""

import json
from collections.abc import Iterator

import httpx

from src.llm.base import LLMError, LLMProvider
from src.llm.retry import make_client

_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLM(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout: float = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self._key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = client or make_client(timeout)

    def _body(self, system: str, user: str, json_mode: bool, stream: bool) -> dict:
        body = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if stream:
            body["stream"] = True
        return body

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}"}

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        try:
            r = self._client.post(_URL, json=self._body(system, user, json_mode, False), headers=self._headers())
            r.raise_for_status()
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMError(f"Groq falló: {type(e).__name__}") from e

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Genera los fragmentos de texto a medida que llegan (SSE de Groq)."""
        try:
            with self._client.stream(
                "POST", _URL, json=self._body(system, user, False, True), headers=self._headers()
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    delta = json.loads(data)["choices"][0].get("delta", {}).get("content")
                    if delta:
                        yield delta
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMError(f"Groq falló: {type(e).__name__}") from e
