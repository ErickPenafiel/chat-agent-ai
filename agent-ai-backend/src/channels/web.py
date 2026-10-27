"""Adapter web mock: sin proveedor externo. Guarda lo enviado en memoria para poder probar el grafo."""

import json
import uuid
from collections import defaultdict
from collections.abc import Mapping

from src.channels.base import (
    InboundEvent,
    InvalidWebhook,
    MediaItem,
    MediaType,
    MessagingChannel,
)


class WebChannel(MessagingChannel):
    name = "web"
    is_real = False

    def __init__(self) -> None:
        self.outbox: dict[str, list[dict]] = defaultdict(list)
        self.history: dict[str, list[dict]] = defaultdict(list)

    def receive(self, body: bytes, headers: Mapping[str, str]) -> list[InboundEvent]:
        try:
            data = json.loads(body)
            user_id = str(data["user_id"])
        except (ValueError, KeyError, TypeError) as e:
            raise InvalidWebhook("se espera JSON con user_id y text") from e
        media = [MediaItem(**m) for m in data.get("media", [])]
        self.history[user_id].append({"role": "user", "text": data.get("text", "")})
        return [InboundEvent(
            channel=self.name, user_id=user_id,
            message_id=str(data.get("message_id") or uuid.uuid4()),
            text=data.get("text", ""), media=media, raw=data,
        )]

    def send_text(self, user_id: str, text: str) -> None:
        self.outbox[user_id].append({"type": "text", "text": text})
        self.history[user_id].append({"role": "assistant", "text": text})

    def send_media(self, user_id: str, url: str, media_type: MediaType, caption: str | None = None) -> None:
        self.outbox[user_id].append({"type": media_type, "url": url, "caption": caption})

    def send_document(self, user_id: str, url: str, filename: str, caption: str | None = None) -> None:
        self.outbox[user_id].append({"type": "document", "url": url, "filename": filename, "caption": caption})

    def fetch_history(self, user_id: str) -> list[dict]:
        return list(self.history[user_id])
