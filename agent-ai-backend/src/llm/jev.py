"""Cliente de Jev (TypeSafe AI): modelo de decisión que devuelve respuestas tipadas con probabilidades."""

import os
from collections.abc import Mapping
from typing import Any

import httpx

from src.core.config import JevConfig
from src.llm.base import LLMError
from src.llm.retry import make_client

URL = "https://api.typesafe.ai/v1/systemone"
KEY_VAR = "TYPESAFE_API_KEY"


class JevClient:
    def __init__(
        self, api_key: str, model: str = "jev-latest", timeout: float = 10, client: httpx.Client | None = None
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client or make_client(timeout)

    def decide(self, state: str, questions: dict[str, Any]) -> dict[str, Any]:
        """Devuelve `answers` (una entrada por pregunta). Lanza LLMError ante cualquier fallo."""
        body = {"state": state, "model": self._model, "questions": questions}
        try:
            r = self._client.post(URL, json=body, headers={"Authorization": f"Bearer {self._key}"})
            r.raise_for_status()
            return r.json()["answers"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMError(f"Jev falló: {type(e).__name__}") from e


def build_jev(cfg: JevConfig | None, env: Mapping[str, str] | None = None) -> JevClient | None:
    """Sin bloque `jev` en tenant.yaml no se usa Jev."""
    if cfg is None:
        return None
    env = os.environ if env is None else env
    key = env.get(KEY_VAR)
    if not key:
        raise RuntimeError(f"falta la variable de entorno {KEY_VAR} para usar jev")
    return JevClient(key, cfg.model, cfg.timeout_seconds)
