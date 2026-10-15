import os
from collections.abc import Mapping

from src.core.config import LLMConfig
from src.llm.anthropic import AnthropicLLM
from src.llm.base import LLMProvider
from src.llm.google import GoogleGenAI
from src.llm.groq import GroqLLM

_KEY_VARS = {"google": "GOOGLE_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY"}
_CLASSES = {"google": GoogleGenAI, "anthropic": AnthropicLLM, "groq": GroqLLM}


def build_llm(cfg: LLMConfig | None, env: Mapping[str, str] | None = None) -> LLMProvider | None:
    """Sin bloque `llm` en tenant.yaml el agente corre sin LLM (solo KB/conectores en crudo)."""
    if cfg is None:
        return None
    env = os.environ if env is None else env
    key = env.get(_KEY_VARS[cfg.provider])
    if not key:
        raise RuntimeError(f"falta la variable de entorno {_KEY_VARS[cfg.provider]} para llm.provider={cfg.provider}")
    return _CLASSES[cfg.provider](
        key, cfg.model, temperature=cfg.temperature, max_tokens=cfg.max_tokens, timeout=cfg.timeout_seconds
    )
