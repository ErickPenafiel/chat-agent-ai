import hashlib
import hmac
import json

import httpx
import pytest
from fastapi.testclient import TestClient as PlainClient

from src.api.app import create_app
from src.channels.base import InvalidWebhook
from src.channels.registry import build_channels
from src.channels.web import WebChannel
from src.channels.whatsapp_cloud_api import WhatsAppCloudAPIChannel
from src.core.config import load_tenant_config
from tests.helpers import authed_client as TestClient


# ---------- web mock ----------
def test_web_receive_and_outbox():
    ch = WebChannel()
    [ev] = ch.receive(json.dumps({"user_id": "u1", "text": "hola"}).encode(), {})
    assert (ev.channel, ev.user_id, ev.text) == ("web", "u1", "hola")
    ch.send_text("u1", "ok")
    ch.send_media("u1", "http://x/a.png", "image", "foto")
    ch.send_document("u1", "http://x/a.pdf", "a.pdf")
    assert [m["type"] for m in ch.outbox["u1"]] == ["text", "image", "document"]


def test_web_rejects_bad_payload():
    with pytest.raises(InvalidWebhook):
        WebChannel().receive(b"no json", {})
    with pytest.raises(InvalidWebhook):
        WebChannel().receive(b'{"text": "x"}', {})


# ---------- whatsapp ----------
SECRET = "s3cret"


def _sign(body: bytes) -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()}


def _wa(handler=None):
    client = httpx.Client(transport=httpx.MockTransport(handler or (lambda r: httpx.Response(200, json={}))))
    return WhatsAppCloudAPIChannel("tok", "123", SECRET, "vt", client=client)


def _payload(messages):
    return json.dumps({"entry": [{"changes": [{"value": {"messages": messages}}]}]}).encode()


def test_wa_receive_text_and_media():
    body = _payload([
        {"from": "591700", "id": "m1", "type": "text", "text": {"body": "hola"}},
        {"from": "591700", "id": "m2", "type": "image", "image": {"id": "img1", "mime_type": "image/jpeg", "caption": "mira"}},
    ])
    e1, e2 = _wa().receive(body, _sign(body))
    assert (e1.user_id, e1.text) == ("591700", "hola")
    assert e2.media[0].id == "img1" and e2.text == "mira"


def test_wa_status_only_webhook_yields_no_events():
    body = json.dumps({"entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]}).encode()
    assert _wa().receive(body, _sign(body)) == []


def test_wa_rejects_bad_signature():
    body = _payload([])
    with pytest.raises(InvalidWebhook):
        _wa().receive(body, {"X-Hub-Signature-256": "sha256=deadbeef"})
    with pytest.raises(InvalidWebhook):
        _wa().receive(body, {})


def test_wa_verify_subscription():
    ch = _wa()
    ok = {"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"}
    assert ch.verify_subscription(ok) == "42"
    with pytest.raises(InvalidWebhook):
        ch.verify_subscription({**ok, "hub.verify_token": "mal"})


def test_wa_send_payloads():
    sent = []

    def handler(req: httpx.Request):
        sent.append((str(req.url), req.headers["authorization"], json.loads(req.content)))
        return httpx.Response(200, json={})

    ch = _wa(handler)
    ch.send_text("591700", "hola")
    ch.send_media("591700", "http://x/a.mp3", "audio", "ignorado")
    ch.send_document("591700", "http://x/a.pdf", "a.pdf", "doc")
    assert sent[0][0] == "https://graph.facebook.com/v21.0/123/messages"
    assert sent[0][1] == "Bearer tok"
    assert sent[0][2] == {"messaging_product": "whatsapp", "to": "591700", "type": "text", "text": {"body": "hola"}}
    assert "caption" not in sent[1][2]["audio"]
    assert sent[2][2]["document"] == {"link": "http://x/a.pdf", "filename": "a.pdf", "caption": "doc"}


def test_wa_send_http_error_raises():
    ch = _wa(lambda r: httpx.Response(401, json={}))
    with pytest.raises(httpx.HTTPStatusError):
        ch.send_text("1", "x")


# ---------- registry ----------
def test_registry():
    assert set(build_channels(["web"])) == {"web"}
    with pytest.raises(ValueError):
        build_channels(["telegrama"])
    with pytest.raises(RuntimeError):
        build_channels(["whatsapp_cloud_api"], env={})


# ---------- extremo a extremo por la API ----------
@pytest.fixture
def client():
    cfg = load_tenant_config("config/tenant.example.yaml")
    return TestClient(create_app(cfg, "sqlite:///:memory:"))


def _send(client, text, user="u1", **extra):
    return client.post("/channels/web/webhook", json={"user_id": user, "text": text, **extra})


def test_web_roundtrip_reaches_outbox(client):
    r = _send(client, "hola")
    assert r.json()["processed"] == 1
    assert client.get("/channels/web/outbox/u1").json()[0]["text"] == r.json()["replies"][0]


def test_duplicate_message_id_processed_once(client):
    _send(client, "hola", message_id="m1")
    _send(client, "hola", message_id="m1")
    assert len(client.get("/channels/web/outbox/u1").json()) == 1


def test_inactive_channel_404(client):
    assert client.post("/channels/whatsapp_cloud_api/webhook", content=b"{}").status_code == 404


def test_bad_web_payload_400(client):
    assert client.post("/channels/web/webhook", content=b"x").status_code == 400


def test_whatsapp_endpoint_with_signature_and_handshake():
    cfg = load_tenant_config("config/tenant.example.yaml")
    app = create_app(cfg, "sqlite:///:memory:", channels={"whatsapp_cloud_api": _wa()})
    c = PlainClient(app)  # sin token: los webhooks de canales reales son públicos (los protege la firma)
    q = {"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"}
    assert c.get("/channels/whatsapp_cloud_api/webhook", params=q).text == "42"
    assert c.get("/channels/whatsapp_cloud_api/webhook", params={**q, "hub.verify_token": "x"}).status_code == 403
    body = _payload([{"from": "591700", "id": "m1", "type": "text", "text": {"body": "hola"}}])
    assert c.post("/channels/whatsapp_cloud_api/webhook", content=body, headers=_sign(body)).json()["processed"] == 1
    assert c.post("/channels/whatsapp_cloud_api/webhook", content=body).status_code == 403


def test_conversation_state_persists_across_turns():
    """La captura multi-turno solo funciona si el checkpointer conserva el estado entre mensajes."""
    from langgraph.checkpoint.memory import MemorySaver

    from src.channels.base import InboundEvent
    from src.core.dispatcher import handle_event
    from src.core.graph import build_graph

    cfg = load_tenant_config("config/tenant.example.yaml")
    g = build_graph(cfg, classifier=lambda m, e: "sales", checkpointer=MemorySaver())
    ch = WebChannel()
    ev = lambda t, i: InboundEvent("web", "u1", i, t)
    handle_event(g, ch, ev("precio?", "1"))
    handle_event(g, ch, ev("Ana", "2"))
    handle_event(g, ch, ev("La Paz", "3"))
    snap = g.get_state({"configurable": {"thread_id": "web:u1"}}).values
    assert snap["capture"] == {"name": "Ana", "city": "La Paz"}
    assert "industry" in ch.outbox["u1"][-1]["text"]
