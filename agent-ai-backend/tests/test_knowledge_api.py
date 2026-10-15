import pytest
from tests.helpers import authed_client as TestClient

from src.api.app import create_app
from src.core.config import load_tenant_config
from src.core.graph import build_graph
from src.nodes.kb_retriever import make_kb_retriever


@pytest.fixture
def app():
    return create_app(load_tenant_config("config/tenant.example.yaml"), "sqlite:///:memory:")


@pytest.fixture
def client(app):
    return TestClient(app)


BLOCK = {"title": "Reiniciar", "content": "Apague y encienda el equipo.", "intents": ["support"]}


def _create(client, **over):
    return client.post("/knowledge-blocks", json={**BLOCK, **over})


def test_create_defaults(client):
    r = _create(client)
    assert r.status_code == 201
    b = r.json()
    assert (b["status"], b["version"], b["language"], b["category"]) == ("published", 1, "es", None)


def test_multiple_intents_and_normalization(client):
    r = _create(client, intents=["Support", " SALES ", "support"], category="Payments")
    assert r.json()["intents"] == ["support", "sales"]
    assert r.json()["category"] == "payments"
    assert len(client.get("/knowledge-blocks", params={"intent": "sales"}).json()) == 1


def test_typo_intent_and_category_rejected(client):
    assert _create(client, intents=["ventas"]).status_code == 422
    assert _create(client, category="Ventas").status_code == 422
    assert client.get("/knowledge-blocks").json() == []


def test_intents_cannot_be_empty(client):
    assert _create(client, intents=[]).status_code == 422


def test_typo_on_update_rejected(client):
    bid = _create(client).json()["id"]
    assert client.patch(f"/knowledge-blocks/{bid}", json={"intents": ["ventas"]}).status_code == 422
    assert client.patch(f"/knowledge-blocks/{bid}", json={"title": "Nuevo"}).json()["title"] == "Nuevo"


def test_steps_reference_attachments_by_id(client):
    att = [{"id": "a1", "type": "image", "url": "http://x/a.png", "alt": "pantalla"}]
    bad = _create(client, attachments=att, steps=[{"text": "p", "attachment_id": "zz"}])
    assert bad.status_code == 422
    ok = _create(client, attachments=att, steps=[{"text": "p", "attachment_id": "a1"}])
    assert ok.status_code == 201
    assert _create(client, attachments=att + att).status_code == 422  # ids duplicados


def test_update_validates_final_combination(client):
    att = [{"id": "a1", "type": "video", "url": "http://x/v.mp4"}]
    bid = _create(client, attachments=att, steps=[{"text": "p", "attachment_id": "a1"}]).json()["id"]
    r = client.patch(f"/knowledge-blocks/{bid}", json={"attachments": []})
    assert r.status_code == 422  # el paso quedaría huérfano


def test_versioning_and_rollback(client):
    bid = _create(client).json()["id"]
    client.patch(f"/knowledge-blocks/{bid}", json={"content": "Otro texto", "note": "cambio"})
    vs = client.get(f"/knowledge-blocks/{bid}/versions").json()
    assert [v["version"] for v in vs] == [1, 2]
    assert vs[1]["note"] == "cambio"
    r = client.post(f"/knowledge-blocks/{bid}/rollback/1")
    assert r.json()["content"] == BLOCK["content"]
    assert r.json()["version"] == 3  # el historial no se reescribe
    assert client.post(f"/knowledge-blocks/{bid}/rollback/99").status_code == 422


def test_filters_and_delete_removes_versions(client, app):
    a = _create(client).json()["id"]
    _create(client, intents=["sales"], status="draft")
    assert len(client.get("/knowledge-blocks", params={"status": "draft"}).json()) == 1
    assert client.delete(f"/knowledge-blocks/{a}").status_code == 204
    assert client.get(f"/knowledge-blocks/{a}").status_code == 404
    assert client.get(f"/knowledge-blocks/{a}/versions").status_code == 404


def test_orphans_detected_when_config_shrinks(app, client):
    _create(client, intents=["support", "sales"], category="payments")
    del app.state.config.intents["sales"]
    app.state.config.categories.remove("payments")
    orphans = client.get("/knowledge-blocks/orphans").json()
    assert orphans[0]["problems"] == ["intent:sales", "category:payments"]


def _graph(app):
    return build_graph(app.state.config, classifier=lambda m, e: "support",
                       retriever=make_kb_retriever(app.state.session_factory))


def _ask(g, msg):
    return g.invoke({"channel": "web", "user_id": "u", "last_user_message": msg})


def test_graph_uses_published_blocks_only(app, client):
    bid = _create(client, status="draft").json()["id"]
    assert "Apague" not in _ask(_graph(app), "como reiniciar el equipo")["reply"]
    client.patch(f"/knowledge-blocks/{bid}", json={"status": "published"})
    assert "Apague y encienda" in _ask(_graph(app), "como reiniciar el equipo")["reply"]


def test_keywords_improve_retrieval(app, client):
    _create(client, content="Procedimiento interno.", keywords=["reinicio"],
            example_questions=["se colgó el sistema"])
    assert "Procedimiento" in _ask(_graph(app), "tengo un reinicio pendiente")["reply"]
    assert "Procedimiento" in _ask(_graph(app), "se colgó el sistema")["reply"]
