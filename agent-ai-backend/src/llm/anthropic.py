"""Anthropic Messages API vía REST."""

import httpx

from src.llm.base import LLMError, LLMProvider
from src.llm.retry import make_client


class AnthropicLLM(LLMProvider):
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

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        if json_mode:  # la API no tiene modo JSON simple: se pide en el prompt
            system += "\n\nResponde únicamente con JSON válido, sin texto adicional."
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {"x-api-key": self._key, "anthropic-version": "2023-06-01"}
        try:
            r = self._client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip()
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMError(f"Anthropic falló: {type(e).__name__}") from e
