import json

import httpx
import pytest

from src.core.config import JevConfig, load_tenant_config
from src.llm.base import LLMError
from src.llm.jev import JevClient, build_jev
from src.nodes.jev_classifier import make_jev_classifier

ENABLED = ["support", "sales", "info", "chat", "escalate"]


def _jev(handler):
    return JevClient("k", client=httpx.Client(transport=httpx.MockTransport(handler)))


def _answer(intent, confidence=0.9, issue=None):
    answers = {"intent": {"type": "choice", "choice": intent, "confidence": confidence}}
    if issue:
        answers["issue"] = {"type": "choice", "choice": issue, "confidence": 0.9}
    return httpx.Response(200, json={"model": "jev-1", "answers": answers, "usage": {}})


def test_request_shape_and_intent():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return _answer("sales")

    classify = make_jev_classifier(_jev(handler), {})
    assert classify("¿cuánto cuesta?", ENABLED) == ("sales", None)
    assert seen["auth"] == "Bearer k"
    q = seen["body"]["questions"]["intent"]
    assert q["type"] == "choice" and set(q["criteria"]) == set(ENABLED)
    assert seen["body"]["state"] == "¿cuánto cuesta?"


def test_issue_question_only_when_issues_exist():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return _answer("support", issue="order_status")

    assert make_jev_classifier(_jev(handler), {}, ["order_status"])("¿y mi pedido?", ENABLED) == (
        "support",
        "order_status",
    )
    assert "issue" in bodies[0]["questions"]
    make_jev_classifier(_jev(handler), {})("hola", ENABLED)
    assert "issue" not in bodies[1]["questions"]


def test_issue_none_is_dropped():
    classify = make_jev_classifier(_jev(lambda r: _answer("support", issue="none")), {}, ["order_status"])
    assert classify("x", ENABLED) == ("support", None)


def test_low_confidence_uses_fallback():
    classify = make_jev_classifier(
        _jev(lambda r: _answer("sales", confidence=0.2)), {}, fallback=lambda m, e: ("info", None)
    )
    assert classify("x", ENABLED) == ("info", None)


def test_failure_falls_back_to_chat_or_fallback():
    boom = _jev(lambda r: httpx.Response(500))
    assert make_jev_classifier(boom, {})("x", ENABLED) == ("chat", None)
    assert make_jev_classifier(boom, {}, fallback=lambda m, e: "support")("x", ENABLED) == ("support", None)


def test_decide_raises_llm_error():
    with pytest.raises(LLMError):
        _jev(lambda r: httpx.Response(401)).decide("x", {})


def test_build_jev():
    assert build_jev(None) is None
    assert isinstance(build_jev(JevConfig(), {"TYPESAFE_API_KEY": "k"}), JevClient)
    with pytest.raises(RuntimeError):
        build_jev(JevConfig(), {})


def test_graph_uses_jev_classifier():
    from src.api.app import create_app
    from src.channels.base import InboundEvent
    from src.channels.web import WebChannel
    from src.core.dispatcher import handle_event

    cfg = load_tenant_config("config/tenant.example.yaml")
    cfg.jev = JevConfig()
    app = create_app(cfg, "sqlite:///:memory:", jev=_jev(lambda r: _answer("escalate")))
    reply = handle_event(app.state.graph, WebChannel(), InboundEvent("web", "u1", "m1", "quiero un humano"))
    assert reply
    assert app.state.graph.get_state({"configurable": {"thread_id": "web:u1"}}).values["intent"] == "escalate"
