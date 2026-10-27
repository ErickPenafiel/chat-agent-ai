from src.core.config import load_tenant_config
from src.nodes.keyword_classifier import make_keyword_classifier

ENABLED = ["support", "sales", "info", "chat", "escalate"]


def _classify():
    return make_keyword_classifier(load_tenant_config("examples/coffee-shop/tenant.demo.yaml"))


def test_matches_ignoring_case_and_accents():
    c = _classify()
    assert c("¿Cuál es el HORARIO?", ENABLED) == "info"
    assert c("quiero una SUSCRIPCIÓN", ENABLED) == "sales"


def test_most_keywords_wins_and_no_match_is_chat():
    c = _classify()
    assert c("tengo un problema y quiero cancelar, hay un error", ENABLED) == "support"
    assert c("hola", ENABLED) == "chat"


def test_disabled_intent_is_ignored():
    assert _classify()("horario de envio", ["chat", "escalate"]) == "chat"


def test_escalate_wins_over_other_matches():
    assert _classify()("quiero hablar con un humano", ENABLED) == "escalate"
