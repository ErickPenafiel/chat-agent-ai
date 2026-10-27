import json
from datetime import UTC, datetime, timedelta

import pytest

from src.api.app import create_app
from src.channels.base import InboundEvent
from src.channels.web import WebChannel
from src.core.config import load_tenant_config
from src.core.dispatcher import handle_event
from src.db.knowledge import KBRules
from src.db.models import ConversationOutcome
from src.eval.corrector import propose_improvements
from src.eval.judge import evaluate_pending, parse_verdict
from src.eval.replay import replay_user
from src.eval.rules import evaluate_rules
from src.eval.simulation import Scenario, load_scenarios, run_scenario
from src.llm.fake import FakeLLM
from tests.helpers import authed_client as TestClient


def make(handler, **cfg_over):
    cfg = load_tenant_config("config/tenant.example.yaml")
    for k, v in cfg_over.items():
        setattr(cfg, k, v)
    fake = FakeLLM(handler)
    app = create_app(cfg, "sqlite:///:memory:", llm=fake)
    return app, fake, TestClient(app)


def agent(system, user, json_mode):
    """LLM falso que sirve a todos los roles según el prompt."""
    if "Clasificas mensajes" in system:
        return json.dumps({"intent": "support", "issue": None})
    if "Evalúas conversaciones" in system:
        return json.dumps({"score": 2, "resolved": False, "issues": [{"type": "missing_kb", "detail": "sin dato"}]})
    if "Simulas ser un cliente" in system:
        return "FIN" if "assistant:" in user else "hola, necesito ayuda con mi cuenta"
    return "respuesta del agente"


def say(app, text, user="u1", mid=None, ch=None):
    return handle_event(app.state.graph, ch or WebChannel(), InboundEvent("web", user, mid or text, text),
                        recorder=app.state.recorder)


def outcomes(app):
    with app.state.session_factory() as db:
        return list(db.query(ConversationOutcome).order_by(ConversationOutcome.id))


# ---------- capa 0: reglas ----------
def T(*replies):
    return [m for r in replies for m in ({"role": "user", "content": "q"}, {"role": "assistant", "content": r})]


def test_rules():
    assert evaluate_rules(T("a", "b"), ["llm", "llm"], False) == []
    assert "repeated_reply" in evaluate_rules(T("a", "a"), ["llm", "llm"], False)
    assert "empty_reply" in evaluate_rules(T(" "), ["llm"], False)
    assert "fallback_reply" in evaluate_rules(T("x"), ["fallback"], False)
    assert "degraded_reply" in evaluate_rules(T("x"), ["llm_error"], False)
    assert "handoff" in evaluate_rules(T("x"), ["llm"], True)
    assert "long_conversation" in evaluate_rules(T(*[str(i) for i in range(16)]), ["llm"] * 16, False)


def test_recorder_accumulates_turns_and_flags_fallback():
    app, _, _ = make(lambda s, u, j: "")  # LLM sin respuesta -> crudo -> fallback
    say(app, "hola", mid="1")
    say(app, "hola otra vez", mid="2")
    [o] = outcomes(app)
    assert o.turns == 2 and len(o.transcript) == 4
    assert "fallback_reply" in o.rule_flags and o.source == "live"


def test_new_conversation_after_session_timeout():
    app, _, _ = make(agent)
    say(app, "hola", mid="1")
    with app.state.session_factory() as db:
        o = db.query(ConversationOutcome).one()
        o.updated_at = datetime.now(UTC) - timedelta(minutes=31)  # timeout del ejemplo: 30
        db.commit()
    say(app, "volví", mid="2")
    assert len(outcomes(app)) == 2


# ---------- capa 0: juez ----------
def test_parse_verdict_validates():
    assert parse_verdict('```json\n{"score": 4, "resolved": true}\n```')["score"] == 4
    for bad in ('{"score": 9}', "nada", '{"resolved": true}'):
        with pytest.raises((ValueError, KeyError)):
            parse_verdict(bad)


def test_judge_only_idle_live_conversations():
    app, _, _ = make(agent)
    say(app, "hola", mid="1")
    st = app.state
    assert evaluate_pending(st.session_factory, st.llm, st.prompts, 30) == {"judged": 0, "failed": 0}  # aún activa
    with st.session_factory() as db:
        o = db.query(ConversationOutcome).one()
        o.updated_at = datetime.now(UTC) - timedelta(minutes=45)
        db.commit()
    assert evaluate_pending(st.session_factory, st.llm, st.prompts, 30) == {"judged": 1, "failed": 0}
    [o] = outcomes(app)
    assert o.judge_score == 2 and o.judge_issues[0]["type"] == "missing_kb"


def test_judge_failure_leaves_pending_for_retry():
    def handler(s, u, j):
        if "Evalúas" in s:
            return "no es json"
        return agent(s, u, j)

    app, _, _ = make(handler)
    say(app, "hola", mid="1")
    with app.state.session_factory() as db:
        db.query(ConversationOutcome).one().updated_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    st = app.state
    assert evaluate_pending(st.session_factory, st.llm, st.prompts, 30) == {"judged": 0, "failed": 1}
    assert outcomes(app)[0].judged_at is None


# ---------- capa 0.5: simulación ----------
def test_simulation_runs_scenario_and_judges():
    app, fake, _ = make(agent)
    st = app.state
    sc = Scenario(id="s1", persona="p", goal="g", max_turns=5)
    oid = run_scenario(st.graph, st.llm, st.prompts, st.recorder, st.session_factory, sc)
    o = [x for x in outcomes(app) if x.id == oid][0]
    assert o.source == "simulation" and o.scenario == "s1"
    assert o.turns == 1  # el simulador responde FIN tras ver la respuesta del agente
    assert o.judge_score == 2
    assert not any(x.source == "live" for x in outcomes(app))


def test_simulation_fixed_opening_and_scenario_file():
    app, fake, _ = make(agent)
    st = app.state
    sc = Scenario(id="s2", persona="p", goal="g", opening="mensaje fijo", max_turns=2)
    run_scenario(st.graph, st.llm, st.prompts, st.recorder, st.session_factory, sc, judge=False)
    assert outcomes(app)[0].transcript[0]["content"] == "mensaje fijo"
    assert outcomes(app)[0].judge_score is None
    assert len(load_scenarios("config/scenarios.example.yaml")) == 2


# ---------- capa 1: feedback ----------
def test_feedback_attaches_to_latest_live_conversation():
    app, _, c = make(agent)
    say(app, "hola", mid="1")
    assert c.post("/conversation-outcomes/feedback", json={"channel": "web", "user_id": "u1", "rating": 2, "comment": "mal"}).status_code == 200
    assert outcomes(app)[0].feedback_rating == 2
    assert c.post("/conversation-outcomes/feedback", json={"channel": "web", "user_id": "nadie", "rating": 3}).status_code == 404
    assert c.post("/conversation-outcomes/feedback", json={"channel": "web", "user_id": "u1", "rating": 9}).status_code == 422


def test_outcomes_api_filters():
    app, _, c = make(agent)
    say(app, "hola", mid="1")
    assert len(c.get("/conversation-outcomes", params={"source": "live"}).json()) == 1
    assert c.get("/conversation-outcomes", params={"source": "simulation"}).json() == []
    assert c.get("/conversation-outcomes/1").json()["turns"] == 1


# ---------- capa 2: corrector ----------
def corrector_handler(proposals):
    def handler(s, u, j):
        if "Revisas conversaciones" in s:
            return json.dumps({"proposals": proposals})
        return agent(s, u, j)

    return handler


def bad_conversation(app):
    say(app, "cuanto cuesta el plan", mid="1")
    with app.state.session_factory() as db:
        o = db.query(ConversationOutcome).one()
        o.judge_score = 1.0
        db.commit()


def run_corrector(app):
    st = app.state
    return propose_improvements(st.session_factory, st.llm, st.prompts, KBRules.from_config(st.config))


def test_corrector_ignores_good_conversations():
    app, _, _ = make(corrector_handler([]))
    say(app, "hola", mid="1")
    with app.state.session_factory() as db:
        db.query(ConversationOutcome).one().judge_score = 5.0
        db.commit()
    assert run_corrector(app)["outcomes"] == 0


def test_corrector_proposes_validates_and_approval_applies():
    props = [
        {"kind": "kb_create", "title": "Precio", "content": "Cuesta [COMPLETAR]", "intents": ["sales"], "rationale": "falta", "evidence": [1]},
        {"kind": "prompt_update", "slug": "agent_support", "text": "Nuevo prompt de {{business_name}}", "rationale": "r", "evidence": [1, 99]},
        {"kind": "kb_create", "title": "X", "content": "Y", "intents": ["ventas"]},             # intención inválida
        {"kind": "prompt_update", "slug": "judge", "text": "me autoapruebo"},                    # protegido
        {"kind": "prompt_update", "slug": "agent_support", "text": "hola {{inventada}}"},       # variable
        {"kind": "kb_update", "block_id": 999, "fields": {"content": "x"}},                      # no existe
        {"kind": "borrar_todo"},
    ]
    app, _, c = make(corrector_handler(props))
    bad_conversation(app)
    res = run_corrector(app)
    assert res == {"outcomes": 1, "proposals": 2, "discarded": 5}
    assert run_corrector(app)["outcomes"] == 0  # ya revisada, no se reprocesa
    listed = c.get("/improvement-proposals", params={"status": "pending"}).json()
    assert [p["kind"] for p in listed] == ["prompt_update", "kb_create"]
    assert listed[0]["evidence_outcome_ids"] == [1]  # el id inventado se descarta
    # nada aplicado todavía
    assert c.get("/knowledge-blocks").json() == []
    assert c.get("/prompts/agent_support").json()["version"] == 1

    kb_id = next(p["id"] for p in listed if p["kind"] == "kb_create")
    pr_id = next(p["id"] for p in listed if p["kind"] == "prompt_update")
    assert c.post(f"/improvement-proposals/{kb_id}/approve").json()["status"] == "approved"
    assert c.get("/knowledge-blocks").json()[0]["title"] == "Precio"
    assert c.get("/knowledge-blocks/1/versions").json()[0]["author"] == "corrector"
    assert c.post(f"/improvement-proposals/{pr_id}/approve").status_code == 200
    assert c.get("/prompts/agent_support").json()["version"] == 2
    assert c.post(f"/improvement-proposals/{pr_id}/approve").status_code == 409  # ya resuelta


def test_stale_proposal_conflicts_and_reject():
    props = [{"kind": "prompt_update", "slug": "agent_support", "text": "Propuesto", "rationale": "r"},
             {"kind": "prompt_update", "slug": "agent_chat", "text": "Otro", "rationale": "r"}]
    app, _, c = make(corrector_handler(props))
    bad_conversation(app)
    run_corrector(app)
    c.put("/prompts/agent_support", json={"text": "alguien lo editó a mano"})
    ids = {p["payload"]["slug"]: p["id"] for p in c.get("/improvement-proposals").json()}
    assert c.post(f"/improvement-proposals/{ids['agent_support']}/approve").status_code == 409
    assert c.get("/prompts/agent_support").json()["text"] == "alguien lo editó a mano"
    r = c.post(f"/improvement-proposals/{ids['agent_chat']}/reject").json()
    assert r["status"] == "rejected"
    assert c.get("/prompts/agent_chat").json()["version"] == 1


def test_corrector_llm_failure_keeps_outcomes_for_retry():
    def handler(s, u, j):
        if "Revisas conversaciones" in s:
            return "basura"
        return agent(s, u, j)

    app, _, _ = make(handler)
    bad_conversation(app)
    assert run_corrector(app) == {"outcomes": 1, "proposals": 0, "discarded": 0}  # JSON ilegible = sin propuestas
    assert outcomes(app)[0].corrected_at is not None


def test_corrector_llm_exception_keeps_outcomes_for_retry():
    from src.llm.base import LLMError

    def handler(s, u, j):
        if "Revisas conversaciones" in s:
            raise LLMError("caído")
        return agent(s, u, j)

    app, _, _ = make(handler)
    bad_conversation(app)
    assert run_corrector(app)["error"] is True
    assert outcomes(app)[0].corrected_at is None
    assert run_corrector(app)["outcomes"] == 1  # se reintenta


# ---------- replay ----------
def test_replay_reruns_user_messages_through_current_agent():
    app, fake, _ = make(agent)
    ch = WebChannel()
    ch.receive(json.dumps({"user_id": "u9", "text": "primera pregunta"}).encode(), {})
    ch.send_text("u9", "respuesta vieja")
    ch.receive(json.dumps({"user_id": "u9", "text": "segunda pregunta"}).encode(), {})
    st = app.state
    oid = replay_user(st.graph, ch, "u9", st.recorder, st.session_factory, st.llm, st.prompts)
    o = [x for x in outcomes(app) if x.id == oid][0]
    assert o.source == "replay" and o.turns == 2
    assert [m["content"] for m in o.transcript if m["role"] == "user"] == ["primera pregunta", "segunda pregunta"]
    assert "respuesta vieja" not in json.dumps(o.transcript)
    assert o.judge_score == 2


def test_whatsapp_channel_has_no_history():
    from tests.test_channels import _wa
    with pytest.raises(NotImplementedError):
        _wa().fetch_history("1")
