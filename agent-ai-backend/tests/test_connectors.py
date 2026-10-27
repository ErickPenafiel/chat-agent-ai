import pytest

from src.api.app import create_app
from src.connectors.base import Connector
from src.connectors.registry import ConnectorRegistry, build_registry
from src.core.config import load_tenant_config
from src.core.graph import build_graph
from tests.helpers import authed_client as TestClient


@pytest.fixture
def cfg():
    return load_tenant_config("config/tenant.example.yaml")


def _run(graph, msg="hola", **extra):
    return graph.invoke({"channel": "web", "user_id": "u1", "last_user_message": msg, **extra})


EXAMPLE = {"connectors": ["example_order_status"]}


def _graph(cfg, **kw):
    cfg.connectors = ["example_order_status"]
    resolver = lambda state: {"id": "A-1"} if state.get("last_user_message") != "sin pedido" else None
    return build_graph(cfg, classifier=lambda m, e: "support", entity_resolver=resolver, **kw)


def test_no_connectors_works_with_rag_only(cfg):
    out = _run(build_graph(cfg, classifier=lambda m, e: "support"), detected_issue="order_status")
    assert out["intent"] == "support"
    assert "connector_results" not in out or out.get("connector_results") in (None, [])


def test_connector_answers_with_live_data(cfg):
    out = _run(_graph(cfg), detected_issue="order_status")
    assert out["connector_results"][0]["found"] is True
    assert out["reply"].startswith("Su pedido A-1 está ")


def test_connector_not_triggered_without_issue(cfg):
    out = _run(_graph(cfg))
    assert not out.get("connector_results")


def test_not_found_falls_back_to_rag(cfg):
    retr = lambda q, i: [{"content": "Texto de la KB."}]
    out = _run(_graph(cfg, retriever=retr), "sin pedido", detected_issue="order_status")
    assert "No encontré un pedido" in out["reply"]
    assert "Texto de la KB." in out["reply"]


def test_found_skips_rag(cfg):
    retr = lambda q, i: [{"content": "Texto de la KB."}]
    out = _run(_graph(cfg, retriever=retr), detected_issue="order_status")
    assert "Texto de la KB." not in out["reply"]


class Boom(Connector):
    id = "boom"
    intents = frozenset({"support"})
    prompt_key = "boom"
    not_found_message = "NO ENCONTRADO"

    def fetch(self, state):
        raise ConnectionError("backend caído")


def test_connector_failure_does_not_crash_nor_claim_not_found(cfg):
    retr = lambda q, i: [{"content": "Texto de la KB."}]
    g = build_graph(cfg, classifier=lambda m, e: "support", retriever=retr, connectors=ConnectorRegistry([Boom()]))
    out = _run(g)
    assert out["connector_results"][0]["error"] == "backend caído"
    assert "NO ENCONTRADO" not in out["reply"]
    assert "Texto de la KB." in out["reply"]


def test_matching_rules():
    class ByIntent(Boom):
        id = "i"
        issues = frozenset()

    class ByIssue(Boom):
        id = "j"
        issues = frozenset({"x"})

    reg = ConnectorRegistry([ByIntent(), ByIssue()])
    assert [c.id for c in reg.match("support", None)] == ["i"]
    assert [c.id for c in reg.match("support", "x")] == ["i", "j"]
    assert [c.id for c in reg.match("sales", "x")] == []


def test_registry_rejects_unknown_and_duplicates():
    with pytest.raises(ValueError):
        build_registry(["no_existe"])
    with pytest.raises(ValueError):
        ConnectorRegistry([Boom(), Boom()])


def test_connectors_endpoint(cfg):
    cfg.connectors = ["example_order_status"]
    c = TestClient(create_app(cfg, "sqlite:///:memory:"))
    body = c.get("/connectors").json()
    assert body["active"][0]["id"] == "example_order_status"
    assert body["active"][0]["issues"] == ["order_status"]
