"""Google Gemini vía REST (generateContent)."""

import httpx

from src.llm.base import LLMError, LLMProvider
from src.llm.retry import make_client


class GoogleGenAI(LLMProvider):
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
        self._url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        self._gen = {"temperature": temperature, "maxOutputTokens": max_tokens}
        self._client = client or make_client(timeout)

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        gen = dict(self._gen)
        if json_mode:
            gen["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen,
        }
        try:
            r = self._client.post(self._url, json=body, headers={"x-goog-api-key": self._key})
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            # Sin respuesta utilizable (error HTTP, o bloqueo por seguridad que no trae candidates).
            raise LLMError(f"Google GenAI falló: {type(e).__name__}") from e
