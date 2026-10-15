import logging

import httpx

from tests.helpers import authed_client as TestClient

from src.api.app import create_app
from src.core.config import load_tenant_config
from src.llm.fake import FakeLLM
from src.llm.groq import GroqLLM
from src.llm.health import verify_llm


# ---------- tope de longitud de entrada ----------
def _app_with_cap(cap):
    seen = []

    def handler(system, user, json_mode):
        seen.append(user)
        return '{"intent": "chat", "issue": null}' if json_mode else "ok"

    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.max_input_chars = cap
    return create_app(cfg, "sqlite:///:memory:", llm=FakeLLM(handler)), seen


def test_long_message_is_truncated_before_reaching_the_llm():
    app, seen = _app_with_cap(50)
    r = TestClient(app).post("/channels/web/webhook", json={"user_id": "u", "text": "a" * 5000})
    assert r.status_code == 200
    assert seen and all("a" * 51 not in u for u in seen)


def test_short_message_is_untouched():
    app, seen = _app_with_cap(50)
    TestClient(app).post("/channels/web/webhook", json={"user_id": "u", "text": "hola"})
    assert any("hola" in u for u in seen)


# ---------- chequeo de arranque del LLM ----------
def _groq(status=None):
    def handler(req):
        if status:
            return httpx.Response(status, json={"error": {}})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    return GroqLLM("K", "m", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_verify_ok():
    assert verify_llm(_groq()) is True
    assert verify_llm(None) is True


def test_verify_reports_missing_model(caplog):
    with caplog.at_level(logging.ERROR):
        assert verify_llm(_groq(404)) is False
    assert "HTTP 404" in caplog.text and "llm.model" in caplog.text


def test_verify_reports_bad_key(caplog):
    with caplog.at_level(logging.ERROR):
        assert verify_llm(_groq(401)) is False
    assert "HTTP 401" in caplog.text


# ---------- verificación anti-alucinación ----------
import json  # noqa: E402

from src.channels.base import InboundEvent  # noqa: E402
from src.channels.web import WebChannel  # noqa: E402
from src.core.dispatcher import handle_event_with_trace  # noqa: E402
from src.nodes.verify import UNSUPPORTED_REPLY  # noqa: E402


def _verified_app(draft, verdict, verify=True, with_block=True):
    """LLM falso: clasifica `support`, redacta `draft` y el verificador devuelve `verdict` (o lanza si es una excepción)."""
    def handler(system, user, json_mode):
        if "Verificas la respuesta" in system:
            if isinstance(verdict, Exception):
                raise verdict
            return json.dumps(verdict) if isinstance(verdict, dict) else verdict
        if json_mode:
            return json.dumps({"intent": "support", "issue": None})
        return draft

    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.verify_responses = verify
    fake = FakeLLM(handler)
    app = create_app(cfg, "sqlite:///:memory:", llm=fake)
    if with_block:
        TestClient(app).post("/knowledge-blocks", json={
            "title": "Reiniciar", "content": "Apague y encienda el equipo.", "intents": ["support"]})
    return app, fake


def _turn(app, text="como reinicio el equipo"):
    ev = InboundEvent("web", "u1", text, text)
    return handle_event_with_trace(app.state.graph, WebChannel(), ev)


def test_supported_reply_passes_unchanged():
    app, _ = _verified_app("Apague y encienda.", {"supported": True, "unsupported_claims": []})
    reply, trace = _turn(app)
    assert reply == "Apague y encienda." and trace["verification"] == "supported"


def test_unsupported_reply_is_replaced_and_history_is_corrected():
    app, _ = _verified_app("Cuesta $50 y llega en 2 días.", {"supported": False, "unsupported_claims": ["$50"]})
    reply, trace = _turn(app)
    assert reply == UNSUPPORTED_REPLY
    assert trace["verification"] == "rejected" and trace["unsupported_claims"] == ["$50"]
    state = app.state.graph.get_state({"configurable": {"thread_id": "web:u1"}}).values
    assert state["messages"][-1]["content"] == UNSUPPORTED_REPLY  # el historial no conserva la alucinación


def test_verifier_receives_context_and_draft():
    app, fake = _verified_app("Apague y encienda.", {"supported": True})
    _turn(app)
    system, user, json_mode = fake.calls[-1]
    assert json_mode and "Verificas la respuesta" in system
    assert "Apague y encienda el equipo." in user and "<draft_reply>\nApague y encienda.\n</draft_reply>" in user


def test_verifier_failure_keeps_the_draft():
    for verdict in (RuntimeError("caído"), "no es json", '{"supported": "quizá"}'):
        app, _ = _verified_app("Borrador.", verdict)
        reply, trace = _turn(app)
        assert reply == "Borrador." and trace["verification"] == "error"


def test_no_facts_to_check_skips_verification_call():
    app, fake = _verified_app("Hola, ¿en qué ayudo?", {"supported": False}, with_block=False)
    reply, trace = _turn(app, "reiniciar")  # sin bloques en la KB: nada que contrastar
    assert reply == "Hola, ¿en qué ayudo?" and trace["verification"] == "skipped"
    assert not any("Verificas la respuesta" in c[0] for c in fake.calls)


def test_verification_is_off_by_default():
    app, fake = _verified_app("Cuesta $50.", {"supported": False}, verify=False)
    reply, trace = _turn(app)
    assert reply == "Cuesta $50." and trace["verification"] is None
    assert not any("Verificas la respuesta" in c[0] for c in fake.calls)
