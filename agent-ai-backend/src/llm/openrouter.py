"""OpenRouter vía su endpoint compatible con OpenAI (chat completions). Acepta imagen, audio y video."""

import json
from collections.abc import Iterator

import httpx

from src.llm.base import LLMError, LLMProvider
from src.llm.retry import make_client

_URL = "https://openrouter.ai/api/v1/chat/completions"


def image_part(url: str) -> dict:
    """Imagen por URL pública o `data:image/...;base64,...`."""
    return {"type": "image_url", "image_url": {"url": url}}


def audio_part(data_b64: str, fmt: str = "wav") -> dict:
    """Audio en base64 (sin prefijo `data:`); `fmt` es la extensión: wav, mp3…"""
    return {"type": "input_audio", "input_audio": {"data": data_b64, "format": fmt}}


def video_part(url: str) -> dict:
    return {"type": "video_url", "video_url": {"url": url}}


class OpenRouterLLM(LLMProvider):
    supports_media = True  # depende del modelo elegido: debe aceptar imagen/audio como entrada

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

    def _body(self, system: str, user: str, json_mode: bool, stream: bool, media: list[dict] | None) -> dict:
        content = [{"type": "text", "text": user}, *media] if media else user
        body = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if stream:
            body["stream"] = True
        return body

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "X-OpenRouter-Title": "chat-agent-ai"}

    def complete(self, system: str, user: str, *, json_mode: bool = False, media: list[dict] | None = None) -> str:
        """`media`: partes de contenido (`image_part`, `audio_part`, `video_part`) que acompañan al mensaje."""
        try:
            r = self._client.post(
                _URL, json=self._body(system, user, json_mode, False, media), headers=self._headers()
            )
            r.raise_for_status()
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMError(f"OpenRouter falló: {type(e).__name__}") from e

    def complete_media(self, system: str, user: str, media: list[dict]) -> str:
        return self.complete(system, user, media=media)

    def stream(self, system: str, user: str, *, media: list[dict] | None = None) -> Iterator[str]:
        """Genera los fragmentos de texto a medida que llegan (SSE). Ignora los comentarios `: ...` de keep-alive."""
        try:
            with self._client.stream(
                "POST", _URL, json=self._body(system, user, False, True, media), headers=self._headers()
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
            raise LLMError(f"OpenRouter falló: {type(e).__name__}") from e
