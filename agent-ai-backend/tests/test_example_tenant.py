import json

import pytest

from src.api.app import create_app
from src.core.config import load_tenant_config
from src.db import knowledge
from src.db.kb_loader import KBFileError, load_kb_file, sync_blocks
from src.db.knowledge import KBRules
from src.eval.simulation import load_scenarios
from src.llm.fake import FakeLLM
from tests.helpers import authed_client as TestClient

EX = "examples/coffee-shop"


@pytest.fixture
def app():
    # LLM falso: el tenant de ejemplo declara un proveedor real y los tests no deben depender de claves ni de red
    return create_app(load_tenant_config(f"{EX}/tenant.yaml"), "sqlite:///:memory:", llm=FakeLLM(lambda s, u, j: ""))


def _sync(app, blocks=None, prune=False):
    rules = KBRules.from_config(app.state.config)
    with app.state.session_factory() as db:
        return sync_blocks(db, rules, blocks if blocks is not None else load_kb_file(f"{EX}/kb.yaml"), prune)


def test_example_files_are_valid_for_its_tenant(app):
    blocks = load_kb_file(f"{EX}/kb.yaml")
    assert len(blocks) >= 8
    assert _sync(app)["created"] == len(blocks)  # pasa la validación de intents/categorías del tenant
    assert len(load_scenarios(f"{EX}/scenarios.yaml")) == 4


def test_template_default_kb_stays_empty():
    a = create_app(load_tenant_config("config/tenant.example.yaml"), "sqlite:///:memory:")
    assert TestClient(a).get("/knowledge-blocks").json() == []


def test_sync_is_idempotent_and_versions_changes(app):
    _sync(app)
    assert _sync(app) == {"created": 0, "updated": 0, "unchanged": len(load_kb_file(f"{EX}/kb.yaml")), "archived": 0}
    blocks = load_kb_file(f"{EX}/kb.yaml")
    blocks[0].content = "Texto nuevo."
    assert _sync(app, blocks)["updated"] == 1
    c = TestClient(app)
    first = c.get("/knowledge-blocks").json()[0]
    assert first["content"] == "Texto nuevo." and first["version"] == 2


def test_prune_archives_only_seed_blocks(app):
    _sync(app)
    c = TestClient(app)
    mine = c.post("/knowledge-blocks", json={"title": "Manual", "content": "x", "intents": ["chat"]}).json()["id"]
    blocks = load_kb_file(f"{EX}/kb.yaml")[1:]
    assert _sync(app, blocks, prune=True)["archived"] == 1
    assert c.get(f"/knowledge-blocks/{mine}").json()["status"] == "published"  # lo creado a mano no se toca
    assert c.get("/knowledge-blocks", params={"status": "archived"}).json()[0]["title"] == "Qué vende Lumbre Café"


def test_invalid_kb_file_rejected_before_touching_db(tmp_path):
    bad = tmp_path / "kb.yaml"
    bad.write_text("blocks:\n  - title: A\n    content: B\n    intents: []\n")
    with pytest.raises(KBFileError):
        load_kb_file(bad)
    dup = tmp_path / "dup.yaml"
    dup.write_text("blocks:\n  - {title: A, content: B, intents: [chat]}\n  - {title: A, content: C, intents: [chat]}\n")
    with pytest.raises(KBFileError):
        load_kb_file(dup)


def test_wrong_category_in_file_fails_sync(app):
    blocks = load_kb_file(f"{EX}/kb.yaml")
    blocks[0].category = "ventas"
    with pytest.raises(knowledge.InvalidBlock):
        _sync(app, blocks)


def test_end_to_end_chat_over_example_kb(app):
    _sync(app)
    # sin LLM: el clasificador por defecto manda a «chat»; se verifica el camino completo hasta la KB con un LLM falso
    def handler(system, user, json_mode):
        if json_mode:
            return json.dumps({"intent": "sales", "issue": None})
        return "ok"

    fake = FakeLLM(handler)
    app2 = create_app(app.state.config, "sqlite:///:memory:", llm=fake)
    _sync(app2)
    r = TestClient(app2).post("/channels/web/webhook", json={"user_id": "u", "text": "cuánto cuesta la bolsa de 1 kg"})
    assert r.json()["replies"] == ["ok"]
    # la última llamada puede ser la del verificador (verify_responses: true en el ejemplo)
    system, user, _ = next(c for c in reversed(fake.calls) if not c[2] and "Verificas la respuesta" not in c[0])
    assert "tú" in system and "Lumbre Café" in system
    assert "30 USD" in user
    assert "city" not in user and "«name»" in user  # responde primero y luego pide el primer dato
