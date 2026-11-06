"""Contrato de proveedor de LLM. El grafo solo ve esto; Google/Anthropic son adapters."""

from abc import ABC, abstractmethod


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    supports_media = False  # True en los proveedores que aceptan imágenes y audio (ver complete_media)

    @abstractmethod
    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        """Una vuelta system+user -> texto. json_mode pide salida JSON cuando el proveedor lo soporta."""

    def complete_media(self, system: str, user: str, media: list[dict]) -> str:
        """Como `complete`, con partes de contenido adjuntas (imagen, audio) al mensaje del usuario."""
        raise LLMError(f"{type(self).__name__} no admite adjuntos")
