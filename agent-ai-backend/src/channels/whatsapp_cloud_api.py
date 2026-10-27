"""Adapter de referencia: WhatsApp Cloud API oficial de Meta."""

import hashlib
import hmac
import json
from collections.abc import Mapping

import httpx

from src.channels.base import (
    InboundEvent,
    InvalidWebhook,
    MediaItem,
    MediaType,
    MessagingChannel,
)

_MEDIA_KINDS = ("image", "audio", "video", "document")


class WhatsAppCloudAPIChannel(MessagingChannel):
    name = "whatsapp_cloud_api"

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        app_secret: str,
        verify_token: str,
        api_version: str = "v21.0",
        client: httpx.Client | None = None,
    ) -> None:
        self._token = access_token
        self._secret = app_secret.encode()
        self._verify_token = verify_token
        self._url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        self._client = client or httpx.Client(timeout=10)

    # --- entrada ---
    def verify_subscription(self, query: Mapping[str, str]) -> str | None:
        if query.get("hub.mode") != "subscribe":
            return None
        if not hmac.compare_digest(query.get("hub.verify_token", ""), self._verify_token):
            raise InvalidWebhook("verify_token incorrecto")
        return query.get("hub.challenge", "")

    def _check_signature(self, body: bytes, headers: Mapping[str, str]) -> None:
        sent = headers.get("x-hub-signature-256", "")
        expected = "sha256=" + hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sent, expected):
            raise InvalidWebhook("firma inválida")

    def receive(self, body: bytes, headers: Mapping[str, str]) -> list[InboundEvent]:
        headers = {k.lower(): v for k, v in headers.items()}
        self._check_signature(body, headers)
        try:
            data = json.loads(body)
        except ValueError as e:
            raise InvalidWebhook("JSON inválido") from e

        events = []
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []):
                    events.append(self._to_event(msg))
        return events

    def _to_event(self, msg: dict) -> InboundEvent:
        kind = msg.get("type")
        text, media = "", []
        if kind == "text":
            text = msg["text"]["body"]
        elif kind in _MEDIA_KINDS:
            m = msg[kind]
            caption = m.get("caption")
            text = caption or ""
            media.append(MediaItem(type=kind, id=m.get("id"), mime_type=m.get("mime_type"), caption=caption))
        elif kind == "button":
            text = msg["button"]["text"]
        elif kind == "interactive":
            reply = msg["interactive"].get("button_reply") or msg["interactive"].get("list_reply") or {}
            text = reply.get("title", "")
        return InboundEvent(channel=self.name, user_id=msg["from"], message_id=msg["id"], text=text, media=media, raw=msg)

    # --- salida ---
    def _post(self, user_id: str, kind: str, body: dict) -> None:
        payload = {"messaging_product": "whatsapp", "to": user_id, "type": kind, kind: body}
        r = self._client.post(self._url, json=payload, headers={"Authorization": f"Bearer {self._token}"})
        r.raise_for_status()

    def send_text(self, user_id: str, text: str) -> None:
        self._post(user_id, "text", {"body": text})

    def send_media(self, user_id: str, url: str, media_type: MediaType, caption: str | None = None) -> None:
        body = {"link": url}
        if caption and media_type != "audio":  # audio no admite caption
            body["caption"] = caption
        self._post(user_id, media_type, body)

    def send_document(self, user_id: str, url: str, filename: str, caption: str | None = None) -> None:
        body = {"link": url, "filename": filename}
        if caption:
            body["caption"] = caption
        self._post(user_id, "document", body)
