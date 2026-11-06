import pytest

from src.eval.golden import GoldenCase, load_golden, norm, run_case, score_case, summarize, wilson

EX = "examples/coffee-shop"


class FakeGraph:
    """Grafo mínimo: responde lo que se le pida y registra lo recuperado."""

    def __init__(self, reply, handoff=False, titles=("Precios",)):
        self.reply, self.handoff, self.titles = reply, handoff, titles

    def invoke(self, state, config):
        return {"reply": self.reply, "handoff": self.handoff, "reply_mode": "llm", "verification": "supported",
                "retrieved": [{"title": t} for t in self.titles]}


def case(**kw):
    base = {"id": "c", "category": "precios", "turns": ["¿Cuánto cuesta?"]}
    return GoldenCase.model_validate({**base, **kw})


def test_example_golden_file_is_valid():
    cases = load_golden(f"{EX}/golden.yaml")
    assert len(cases) >= 30
    assert {c.category for c in cases} >= {"precios", "escalamiento", "fuera_de_alcance", "seguridad"}


def test_norm_strips_accents_and_case():
    assert norm("Suscripción MENSUAL") == "suscripcion mensual"


def test_passing_case():
    c = case(must_include=[r"\b30\b"], expect_handoff=False, expect_blocks=["Precios"])
    r = score_case(c, run_case(FakeGraph("La bolsa de 1 kg cuesta 30 USD."), c))
    assert r["passed"] and r["checks"] == {"content": True, "no_invention": None, "handoff": True, "retrieval": True}


def test_missing_fact_fails():
    c = case(must_include=[r"\b30\b"])
    r = score_case(c, run_case(FakeGraph("Cuesta bastante."), c))
    assert not r["passed"] and r["missing"] == [r"\b30\b"]


def test_forbidden_claim_fails():
    c = case(must_not_include=["aceptamos efectivo"])
    r = score_case(c, run_case(FakeGraph("Claro, aceptamos efectivo."), c))
    assert not r["passed"] and r["forbidden_found"] == ["aceptamos efectivo"]


def test_handoff_expected_and_unexpected():
    want = case(expect_handoff=True)
    assert not score_case(want, run_case(FakeGraph("ok", handoff=False), want))["passed"]
    dont = case(expect_handoff=False)
    assert not score_case(dont, run_case(FakeGraph("ok", handoff=True), dont))["passed"]


def test_retrieval_miss_fails():
    c = case(expect_blocks=["Medios de pago"])
    assert not score_case(c, run_case(FakeGraph("ok"), c))["passed"]


def test_accents_do_not_break_matching():
    c = case(must_include=["suscripcion"])
    assert score_case(c, run_case(FakeGraph("Tu suscripción llega cada mes."), c))["passed"]


def test_invalid_regex_is_rejected():
    with pytest.raises(ValueError):
        case(must_include=["("])


def test_summary_counts_and_interval():
    cs = [case(id="a", expect_handoff=True), case(id="b", expect_handoff=False), case(id="c", expect_handoff=False)]
    graphs = {"a": FakeGraph("ok", handoff=True), "b": FakeGraph("ok", handoff=True), "c": FakeGraph("ok")}
    rs = [score_case(c, run_case(graphs[c.id], c)) for c in cs]
    s = summarize(cs, rs)
    assert s["cases"] == 3 and s["passed"] == 2
    assert s["escalation_recall"] == 1.0 and s["false_escalations"] == 1
    lo, hi = s["pass_rate_ci95"]
    assert lo < 2 / 3 < hi


def test_wilson_is_wide_with_few_cases():
    lo, hi = wilson(34, 40)
    assert lo < 0.85 < hi and hi - lo > 0.1
    assert wilson(0, 0) == (0.0, 0.0)


def test_llm_error_makes_case_invalid_and_excluded():
    class Broken(FakeGraph):
        def invoke(self, state, config):
            return {**super().invoke(state, config), "reply_mode": "llm_error"}

    cs = [case(id="a", must_include=["ok"]), case(id="b", must_include=["ok"])]
    rs = [score_case(cs[0], run_case(FakeGraph("ok"), cs[0])), score_case(cs[1], run_case(Broken("ok"), cs[1]))]
    assert rs[1]["invalid"] and not rs[1]["passed"]  # el texto crudo contenía el dato, pero no mide al agente
    s = summarize(cs, rs)
    assert s["cases"] == 1 and s["invalid_cases"] == 1 and s["pass_rate"] == 1.0
