import json

import httpx
import pytest
from tests.helpers import authed_client as TestClient
from langgraph.checkpoint.memory import MemorySaver

from src.api.app import create_app
from src.channels.base import InboundEvent
from src.channels.web import WebChannel
from src.core.config import LLMConfig, load_tenant_config
from src.core.dispatcher import handle_event
from src.llm.anthropic import AnthropicLLM
from src.llm.base import LLMError
from src.llm.factory import build_llm
from src.llm.fake import FakeLLM
from src.llm.google import GoogleGenAI


# ---------- proveedores ----------
def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_google_request_and_parse():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"], seen["key"], seen["body"] = str(req.url), req.headers["x-goog-api-key"], json.loads(req.content)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ho"}, {"text": "la"}]}}]})

    llm = GoogleGenAI("K", "gemini-x", client=_client(handler))
    assert llm.complete("sys", "hola", json_mode=True) == "hola"
    assert seen["url"].endswith("/models/gemini-x:generateContent")
    assert seen["key"] == "K"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "sys"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_google_blocked_response_raises_llmerror():
    llm = GoogleGenAI("K", "m", client=_client(lambda r: httpx.Response(200, json={"promptFeedback": {}})))
    with pytest.raises(LLMError):
        llm.complete("s", "u")


def test_anthropic_request_and_parse():
    seen = {}

    def handler(req: httpx.Request):
        seen["headers"], seen["body"] = req.headers, json.loads(req.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    llm = AnthropicLLM("K", "claude-x", client=_client(handler))
    assert llm.complete("sys", "hola") == "ok"
    assert seen["headers"]["x-api-key"] == "K" and seen["headers"]["anthropic-version"]
    assert seen["body"]["system"] == "sys" and seen["body"]["model"] == "claude-x"
    with pytest.raises(LLMError):
        AnthropicLLM("K", "m", client=_client(lambda r: httpx.Response(500))).complete("s", "u")


def test_factory():
    assert build_llm(None) is None
    cfg = LLMConfig(provider="google", model="m")
    assert isinstance(build_llm(cfg, {"GOOGLE_API_KEY": "k"}), GoogleGenAI)
    assert isinstance(build_llm(LLMConfig(provider="anthropic", model="m"), {"ANTHROPIC_API_KEY": "k"}), AnthropicLLM)
    with pytest.raises(RuntimeError):
        build_llm(cfg, {})


# ---------- app con LLM falso ----------
def _app(handler, connectors=(), **cfg_over):
    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.connectors = list(connectors)
    for k, v in cfg_over.items():
        setattr(cfg, k, v)
    fake = FakeLLM(handler)
    return create_app(cfg, "sqlite:///:memory:", llm=fake), fake


def _classifier_then(reply_fn, intent="support", issue=None):
    def handler(system, user, json_mode):
        if json_mode:
            return json.dumps({"intent": intent, "issue": issue})
        return reply_fn(system, user)

    return handler


def _say(app, text, user="u1", mid=None):
    ch = WebChannel()
    reply = handle_event(app.state.graph, ch, InboundEvent("web", user, mid or text, text))
    return reply


def test_prompts_seeded_from_intents_and_connectors():
    app, _ = _app(lambda *a: "x", connectors=["example_order_status"])
    slugs = set(app.state.prompts.defaults)
    assert {"tone", "intent_classifier", "handoff", "agent_support", "agent_sales", "agent_chat",
            "connector_example_order_status"} <= slugs
    assert "agent_escalate" not in slugs
    app2, _ = _app(lambda *a: "x")
    assert "connector_example_order_status" not in app2.state.prompts.defaults


def test_response_uses_kb_context_and_tone():
    app, fake = _app(_classifier_then(lambda s, u: "Respuesta LLM"))
    c = TestClient(app)
    c.post("/knowledge-blocks", json={"title": "Reiniciar", "content": "Apague y encienda.", "intents": ["support"]})
    assert _say(app, "como reiniciar el equipo") == "Respuesta LLM"
    system, user, _ = fake.calls[-1]
    assert "usted" in system and "Negocio Ejemplo" in system  # tono + variable del negocio
    assert "Apague y encienda." in user and "<customer_message>" in user


def test_classifier_routes_escalate_to_handoff_prompt():
    app, fake = _app(_classifier_then(lambda s, u: "Lo derivo.", intent="escalate"))
    assert _say(app, "quiero hablar con alguien") == "Lo derivo."
    assert "derivas con una persona" in fake.calls[-1][0]


def test_classifier_failure_falls_back_to_chat():
    def handler(system, user, json_mode):
        if json_mode:
            return "esto no es json"
        return "ok"

    app, fake = _app(handler)
    _say(app, "hola")
    assert "Responde de forma breve" in fake.calls[-1][0]  # agent_chat


def test_llm_failure_falls_back_to_raw_reply():
    def handler(system, user, json_mode):
        if json_mode:
            return json.dumps({"intent": "support"})
        raise LLMError("caído")

    app, _ = _app(handler)
    TestClient(app).post("/knowledge-blocks", json={"title": "R", "content": "Texto crudo reiniciar.", "intents": ["support"]})
    assert "Texto crudo" in _say(app, "reiniciar")


def test_connector_prompt_and_data_reach_llm():
    app, fake = _app(_classifier_then(lambda s, u: "Su pedido va en camino", issue="order_status"),
                     connectors=["example_order_status"])
    # sin resolver de entidad no hay dato; se inyecta uno reemplazando el nodo vía estado directo:
    from src.core.graph import build_graph
    g = build_graph(app.state.config, llm=fake, prompts=app.state.prompts, connectors=app.state.connectors,
                    entity_resolver=lambda s: {"id": "A-1"})
    out = g.invoke({"channel": "web", "user_id": "u", "last_user_message": "donde esta mi pedido"})
    system, user, _ = fake.calls[-1]
    assert "datos en vivo del sistema" in system
    assert '<system_data id="example_order_status">' in user and '"order_id": "A-1"' in user
    assert out["reply"] == "Su pedido va en camino"


def test_unknown_issue_from_llm_is_dropped():
    app, _ = _app(_classifier_then(lambda s, u: "ok", issue="inventado"))
    from src.core.graph import build_graph
    g = build_graph(app.state.config, llm=app.state.llm, prompts=app.state.prompts)
    out = g.invoke({"channel": "web", "user_id": "u", "last_user_message": "x"})
    assert out["detected_issue"] is None


# ---------- captura multi-turno con LLM ----------
def test_capture_flow_answers_first_then_asks_then_thanks():
    app, fake = _app(_classifier_then(lambda s, u: "R", intent="sales"))
    TestClient(app).post("/knowledge-blocks", json={"title": "Precio", "content": "Cuesta 10.", "intents": ["sales"]})
    _say(app, "precio", mid="1")
    assert "pide con naturalidad el dato «name»" in fake.calls[-1][1]
    _say(app, "Ana", mid="2")
    assert "«city»" in fake.calls[-1][1]
    assert "Cuesta 10." not in fake.calls[-1][1]  # no se vuelve a responder la consulta vieja
    _say(app, "La Paz", mid="3")
    _say(app, "Retail", mid="4")
    assert "agradécele" in fake.calls[-1][1]


def test_capture_before_answer_then_answers_pending_question():
    app, fake = _app(_classifier_then(lambda s, u: "R", intent="sales"))
    app.state.config.intents["sales"].capture_before_answer = True
    TestClient(app).post("/knowledge-blocks", json={"title": "Precio", "content": "Cuesta 10.", "intents": ["sales"]})
    _say(app, "precio", mid="1")
    assert "Aún no respondas" in fake.calls[-1][1] and "Cuesta 10." not in fake.calls[-1][1]
    _say(app, "Ana", mid="2")
    _say(app, "La Paz", mid="3")
    _say(app, "Retail", mid="4")
    user = fake.calls[-1][1]
    assert "Cuesta 10." in user and "<customer_message>\nprecio" in user
    assert "responde la consulta que dejó pendiente" in user


def test_followup_reply_is_not_reclassified_while_capturing():
    app, fake = _app(_classifier_then(lambda s, u: "R", intent="sales"))
    _say(app, "precio", mid="1")
    n = sum(1 for c in fake.calls if c[2])
    _say(app, "Ana", mid="2")
    assert sum(1 for c in fake.calls if c[2]) == n  # no hubo otra llamada de clasificación


# ---------- API de prompts ----------
@pytest.fixture
def client():
    app, _ = _app(lambda *a: "x")
    return TestClient(app)


def test_prompts_api_edit_version_rollback(client):
    p = client.get("/prompts/agent_support").json()
    assert p["version"] == 1
    r = client.put("/prompts/agent_support", json={"text": "Nuevo para {{business_name}}", "note": "n"})
    assert r.json()["version"] == 2
    assert client.get("/prompts/agent_support").json()["text"].startswith("Nuevo")
    rb = client.post("/prompts/agent_support/rollback/1").json()
    assert rb["version"] == 3 and rb["text"] == p["text"]
    assert [v["version"] for v in client.get("/prompts/agent_support/versions").json()] == [1, 2, 3]
    assert client.post("/prompts/agent_support/rollback/9").status_code == 422


def test_prompts_api_rejects_unknown_slug_and_variables(client):
    assert client.get("/prompts/agent_nada").status_code == 404
    assert client.put("/prompts/nope", json={"text": "x"}).status_code == 404
    assert client.put("/prompts/tone", json={"text": "hola {{inventada}}"}).status_code == 422


def test_edit_applies_to_next_message_and_seed_does_not_overwrite():
    app, fake = _app(_classifier_then(lambda s, u: "R"))
    c = TestClient(app)
    c.put("/prompts/agent_support", json={"text": "PROMPT EDITADO"})
    _say(app, "hola", mid="1")
    assert "PROMPT EDITADO" in fake.calls[-1][0]
    assert app.state.prompts.seed() == []  # re-sembrar no pisa lo editado


def test_web_stream_sse(client):
    r = client.get("/channels/web/stream", params={"user_id": "u1", "text": "hola"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in r.text
