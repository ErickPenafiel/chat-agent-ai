"""Contrato de canal de mensajería. El grafo nunca conoce al proveedor, solo estos tipos."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

MediaType = Literal["image", "audio", "video", "document"]


class InvalidWebhook(Exception):
    """Firma inválida o payload que no es del proveedor."""


@dataclass(frozen=True)
class MediaItem:
    type: MediaType
    id: str | None = None  # id en el proveedor (se descarga después)
    url: str | None = None
    mime_type: str | None = None
    caption: str | None = None


@dataclass(frozen=True)
class InboundEvent:
    channel: str
    user_id: str  # identificador del cliente en el canal (teléfono, session id…)
    message_id: str
    text: str = ""
    media: list[MediaItem] = field(default_factory=list)
    raw: Any = None


class MessagingChannel(ABC):
    name: str
    # Canales con is_real=False no producen side-effects externos (se usan para gating de tickets, alertas, etc.).
    is_real: bool = True

    @abstractmethod
    def receive(self, body: bytes, headers: Mapping[str, str]) -> list[InboundEvent]:
        """Normaliza el webhook del proveedor. Notificaciones sin mensaje (estados) devuelven []."""

    @abstractmethod
    def send_text(self, user_id: str, text: str) -> None: ...

    @abstractmethod
    def send_media(self, user_id: str, url: str, media_type: MediaType, caption: str | None = None) -> None: ...

    @abstractmethod
    def send_document(self, user_id: str, url: str, filename: str, caption: str | None = None) -> None: ...

    def fetch_history(self, user_id: str) -> list[dict]:
        """[{"role": "user"|"assistant", "text": str}] de un cliente, para replay. No todos los canales lo permiten."""
        raise NotImplementedError(f"el canal {self.name!r} no expone historial")

    def verify_subscription(self, query: Mapping[str, str]) -> str | None:
        """Handshake GET de algunos proveedores. Devuelve lo que hay que responder, o None si no aplica."""
        return None
