import pytest

from src.core.config import load_tenant_config
from src.core.graph import build_graph


@pytest.fixture
def cfg():
    return load_tenant_config("config/tenant.example.yaml")


def _run(graph, msg, **extra):
    return graph.invoke({"channel": "web", "user_id": "u1", "last_user_message": msg, **extra})


def test_chat_without_kb_uses_fallback(cfg):
    out = _run(build_graph(cfg), "hola")
    assert out["intent"] == "chat"
    assert out["reply"]


def test_escalate_goes_to_handoff(cfg):
    out = _run(build_graph(cfg, classifier=lambda m, e: "escalate"), "quiero un humano")
    assert out["handoff"] is True


def test_unknown_intent_falls_back_to_chat(cfg):
    out = _run(build_graph(cfg, classifier=lambda m, e: "inventada"), "x")
    assert out["intent"] == "chat"


def test_intent_normalized(cfg):
    out = _run(build_graph(cfg, classifier=lambda m, e: "Support"), "x")
    assert out["intent"] == "support"


def test_sales_answers_first_then_captures(cfg):
    retr = lambda q, i: [{"content": "El plan cuesta 10."}]
    out = _run(build_graph(cfg, classifier=lambda m, e: "sales", retriever=retr), "precio?")
    assert out["reply"].startswith("El plan cuesta 10.")
    assert "name" in out["reply"]
    assert out["awaiting_capture_field"] == "name"


def test_capture_before_answer_withholds_answer(cfg):
    cfg.intents["sales"].capture_before_answer = True
    retr = lambda q, i: [{"content": "El plan cuesta 10."}]
    out = _run(build_graph(cfg, classifier=lambda m, e: "sales", retriever=retr), "precio?")
    assert "El plan cuesta" not in out["reply"]
    assert out["pending_question"] == "precio?"


def test_capture_progresses_through_fields(cfg):
    g = build_graph(cfg, classifier=lambda m, e: "sales")
    out = _run(g, "precio?")
    out = _run(g, "Ana", capture=out["capture"], awaiting_capture_field=out["awaiting_capture_field"])
    assert out["capture"] == {"name": "Ana"}
    assert out["awaiting_capture_field"] == "city"


def test_media_node_included_when_enabled(cfg):
    cfg.media_enabled = True
    out = _run(build_graph(cfg), "hola")
    assert "transcript" in out


def test_question_while_awaiting_capture_is_not_stored_as_the_field(cfg):
    retr = lambda q, i: [{"content": f"Respuesta a: {q}"}]
    g = build_graph(cfg, classifier=lambda m, e: "sales", retriever=retr)
    out = _run(g, "precio?")
    out = _run(g, "¿Y la de 250 g?", capture=out["capture"], awaiting_capture_field=out["awaiting_capture_field"])
    assert out["capture"] == {}  # la pregunta no es el nombre
    assert "Respuesta a: ¿Y la de 250 g?" in out["reply"]  # se responde la consulta nueva
    assert out["awaiting_capture_field"] == "name"  # y se sigue pidiendo el dato


def test_asking_for_a_person_while_awaiting_capture_escalates(cfg):
    first = _run(build_graph(cfg, classifier=lambda m, e: "sales"), "precio?")
    g = build_graph(cfg, classifier=lambda m, e: "escalate" if "persona" in m else "sales")
    out = _run(g, "Quiero hablar con una persona", capture=first["capture"],
               awaiting_capture_field=first["awaiting_capture_field"])
    assert out["handoff"] is True
    assert out["capture"] == {}  # no se guarda como nombre
    # y una respuesta normal sigue siendo el dato
    ok = _run(g, "Ana", capture=first["capture"], awaiting_capture_field=first["awaiting_capture_field"])
    assert ok["capture"] == {"name": "Ana"}
