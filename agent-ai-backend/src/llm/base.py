"""Contrato de proveedor de LLM. El grafo solo ve esto; Google/Anthropic son adapters."""

from abc import ABC, abstractmethod


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Una vuelta system+user -> texto. json_mode pide salida JSON cuando el proveedor lo soporta."""
