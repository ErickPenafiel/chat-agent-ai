"""Une canal y grafo: evento entrante -> grafo -> respuesta saliente por el mismo canal."""

import logging
from collections import OrderedDict
from dataclasses import asdict, replace

from src.channels.base import InboundEvent, MessagingChannel

log = logging.getLogger(__name__)


class Deduper:
    """Los proveedores reintentan webhooks; un mensaje no debe procesarse dos veces."""

    def __init__(self, max_size: int = 5000) -> None:
        self._seen: OrderedDict[tuple[str, str], None] = OrderedDict()
        self._max = max_size

    def seen(self, event: InboundEvent) -> bool:
        return (event.channel, event.message_id) in self._seen

    def mark(self, event: InboundEvent) -> None:
        self._seen[(event.channel, event.message_id)] = None
        while len(self._seen) > self._max:
            self._seen.popitem(last=False)


def turn_input(event: InboundEvent) -> dict:
    """Entrada de un turno. Resetea los campos por-turno para que no arrastren del checkpoint anterior."""
    return {
        "channel": event.channel,
        "user_id": event.user_id,
        "media": [asdict(m) for m in event.media],
        "last_user_message": event.text,
        "transcript": None,
        "detected_issue": None,
        "connector_results": [],
        "retrieved": [],
        "response_parts": [],
        "capture_prompt": None,
        "handoff": False,
        "capture_done": False,
        "answer_pending": False,
        "reply": "",
        "reply_mode": "",
        "verification": None,
        "unsupported_claims": [],
    }


def handle_event_with_trace(
    graph, channel: MessagingChannel, event: InboundEvent, deduper: Deduper | None = None, recorder=None,
    max_input_chars: int | None = None,
) -> tuple[str | None, dict | None]:
    if deduper and deduper.seen(event):
        return None, None
    if max_input_chars and len(event.text) > max_input_chars:
        log.warning("mensaje de %s truncado: %d -> %d caracteres", event.user_id, len(event.text), max_input_chars)
        event = replace(event, text=event.text[:max_input_chars])
    thread = {"configurable": {"thread_id": f"{event.channel}:{event.user_id}"}}
    out = graph.invoke(turn_input(event), thread)
    channel.send_text(event.user_id, out["reply"])
    if recorder:
        recorder.record_turn(thread["configurable"]["thread_id"], event.channel, event.user_id, event.text, out)
    if deduper:  # se marca tras el éxito: si falla, el reintento del proveedor sí se procesa
        deduper.mark(event)
    trace = {
        "intent": out.get("intent"),
        "detected_issue": out.get("detected_issue"),
        "retrieved_blocks": [
            {"id": b.get("id"), "title": b.get("title"), "category": b.get("category")}
            for b in out.get("retrieved", [])
            if isinstance(b, dict)
        ],
        "connectors": [
            {"id": c.get("id"), "found": c.get("found")}
            for c in out.get("connector_results", [])
            if isinstance(c, dict)
        ],
        "handoff": bool(out.get("handoff")),
        "reply_mode": out.get("reply_mode"),
        "verification": out.get("verification"),
        "unsupported_claims": out.get("unsupported_claims", []),
        "capture": out.get("capture", {}),
        "capture_done": out.get("capture_done", False),
    }
    return out["reply"], trace


def handle_event(
    graph, channel: MessagingChannel, event: InboundEvent, deduper: Deduper | None = None, recorder=None,
    max_input_chars: int | None = None,
) -> str | None:
    reply, _ = handle_event_with_trace(graph, channel, event, deduper, recorder, max_input_chars)
    return reply

