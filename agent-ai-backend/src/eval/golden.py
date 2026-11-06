"""Capa 0.7 — casos dorados: preguntas fijas con la respuesta esperada, calificadas sin LLM.

Complementa a la simulación (variable, la juzga un LLM): aquí cada caso dice qué datos debe traer la
respuesta, qué no puede afirmar, si debe pasar a una persona y qué bloques de la KB debía recuperar.
Así dos corridas son comparables y un cambio de prompt, modelo o KB se mide con los mismos casos.
"""

import math
import re
import time
import unicodedata
import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.channels.base import InboundEvent
from src.core.dispatcher import turn_input


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    turns: list[str] = Field(min_length=1)  # mensajes del cliente, en orden
    # Expresiones regulares (sin tildes ni mayúsculas) que TODAS deben aparecer en la respuesta final.
    must_include: list[str] = []
    # Ninguna puede aparecer en ninguna respuesta: afirmaciones inventadas o filtraciones.
    must_not_include: list[str] = []
    expect_handoff: bool | None = None  # None = no se evalúa
    expect_blocks: list[str] = []  # títulos de la KB que debían recuperarse en algún turno
    note: str | None = None

    @model_validator(mode="after")
    def _valid_regex(self):
        for p in [*self.must_include, *self.must_not_include]:
            try:
                re.compile(p)
            except re.error as e:
                raise ValueError(f"expresión regular inválida en {self.id!r}: {p!r} ({e})") from e
        return self


def load_golden(path: str | Path) -> list[GoldenCase]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cases = [GoldenCase.model_validate(c) for c in data["cases"]]
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de casos duplicados")
    return cases


def norm(text: str) -> str:
    """Minúsculas y sin tildes: las expresiones del caso se escriben así."""
    t = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def run_case(graph, case: GoldenCase) -> dict:
    """Corre el caso contra el grafo (un hilo nuevo por caso) y devuelve lo observado."""
    user_id = f"golden-{case.id}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": f"golden:{user_id}"}}
    replies, handoff, modes, titles, verdicts = [], False, [], set(), []
    t0 = time.perf_counter()
    for n, text in enumerate(case.turns):
        out = graph.invoke(turn_input(InboundEvent("golden", user_id, f"{user_id}-{n}", text)), config)
        replies.append(out.get("reply", ""))
        handoff = handoff or bool(out.get("handoff"))
        modes.append(out.get("reply_mode") or "")
        verdicts.append(out.get("verification"))
        titles |= {norm(b.get("title", "")) for b in out.get("retrieved", []) if isinstance(b, dict)}
    return {"replies": replies, "handoff": handoff, "modes": modes, "titles": titles,
            "verification": verdicts, "seconds": time.perf_counter() - t0}


def score_case(case: GoldenCase, obs: dict) -> dict:
    """Cada comprobación es True/False; None si el caso no la pide. `passed` exige todas las pedidas."""
    last = norm(obs["replies"][-1])
    everything = norm("\n".join(obs["replies"]))
    missing = [p for p in case.must_include if not re.search(p, last, re.S)]
    forbidden = [p for p in case.must_not_include if re.search(p, everything, re.S)]
    checks = {
        "content": (not missing) if case.must_include else None,
        "no_invention": (not forbidden) if case.must_not_include else None,
        "handoff": (obs["handoff"] == case.expect_handoff) if case.expect_handoff is not None else None,
        "retrieval": all(norm(t) in obs["titles"] for t in case.expect_blocks) if case.expect_blocks else None,
    }
    # Un error del LLM (cuota, red) deja la respuesta en crudo: el caso no mide al agente y no cuenta ni a favor ni en contra.
    invalid = "llm_error" in obs["modes"]
    return {"id": case.id, "category": case.category, "checks": checks, "invalid": invalid,
            "passed": all(v for v in checks.values() if v is not None) and not invalid,
            "missing": missing, "forbidden_found": forbidden, "handoff": obs["handoff"],
            "modes": obs["modes"], "seconds": round(obs["seconds"], 2), "last_reply": obs["replies"][-1]}


def wilson(ok: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza del 95 % para una proporción. Con pocos casos es ancho: es lo honesto."""
    if n == 0:
        return (0.0, 0.0)
    p = ok / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(cases: list[GoldenCase], all_results: list[dict]) -> dict:
    invalid = sum(r["invalid"] for r in all_results)
    results = [r for r in all_results if not r["invalid"]]  # solo los casos que de verdad midieron al agente
    n = len(results)
    passed = sum(r["passed"] for r in results)
    by_cat: dict[str, list[bool]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["passed"])
    want = {c.id: c.expect_handoff for c in cases}
    should = [r for r in results if want[r["id"]] is True]
    shouldnt = [r for r in results if want[r["id"]] is False]
    retr = [r for r in results if r["checks"]["retrieval"] is not None]
    inv = [r for r in results if r["checks"]["no_invention"] is not None]
    modes = [m for r in results for m in r["modes"]]
    lo, hi = wilson(passed, n)
    return {
        "cases": n, "invalid_cases": invalid, "passed": passed, "pass_rate": passed / n if n else 0.0, "pass_rate_ci95": [round(lo, 3), round(hi, 3)],
        "by_category": {k: {"passed": sum(v), "cases": len(v)} for k, v in sorted(by_cat.items())},
        "escalation_recall": (sum(r["handoff"] for r in should) / len(should)) if should else None,
        "false_escalations": sum(r["handoff"] for r in shouldnt),
        "cases_that_should_not_escalate": len(shouldnt),
        "retrieval_hit_rate": (sum(r["checks"]["retrieval"] for r in retr) / len(retr)) if retr else None,
        "no_invention_rate": (sum(r["checks"]["no_invention"] for r in inv) / len(inv)) if inv else None,
        "degraded_replies": sum(m == "fallback" for m in modes),
        "avg_seconds": round(sum(r["seconds"] for r in results) / n, 2) if n else 0.0,
    }


def render_markdown(summary: dict, results: list[dict], title: str) -> str:
    s = summary
    pct = lambda v: "n/a" if v is None else f"{v:.0%}"  # noqa: E731
    lines = [f"# {title}", "",
             f"**Resueltos: {s['passed']}/{s['cases']} ({pct(s['pass_rate'])})**, intervalo de confianza 95 %: "
             f"{s['pass_rate_ci95'][0]:.0%} a {s['pass_rate_ci95'][1]:.0%}. Con pocos casos el intervalo es ancho: no leas el porcentaje como exacto.", "",
             "| Métrica | Valor |", "|---|---|",
             f"| Escalamiento correcto (de los que debían pasar a una persona) | {pct(s['escalation_recall'])} |",
             f"| Escalamientos de más (de {s['cases_that_should_not_escalate']} que no debían) | {s['false_escalations']} |",
             f"| Recuperó el bloque correcto de la KB | {pct(s['retrieval_hit_rate'])} |",
             f"| No afirmó nada de lo prohibido | {pct(s['no_invention_rate'])} |",
             f"| Casos descartados por error del LLM tras reintentar | {s['invalid_cases']} |",
             f"| Respuestas sin nada que decir (fallback) | {s['degraded_replies']} |",
             f"| Segundos promedio por caso | {s['avg_seconds']} |", "",
             "| Categoría | Resueltos |", "|---|---|"]
    lines += [f"| {k} | {v['passed']}/{v['cases']} |" for k, v in s["by_category"].items()]
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines += ["", f"## Fallos ({len(failed)})", ""]
        for r in failed:
            bad = [k for k, v in r["checks"].items() if v is False]
            lines += [f"- **{r['id']}** ({r['category']}): falló {', '.join(bad)}"
                      + (f"; faltó {r['missing']}" if r["missing"] else "")
                      + (f"; dijo algo prohibido {r['forbidden_found']}" if r["forbidden_found"] else ""),
                      f"  > {r['last_reply'][:240].replace(chr(10), ' ')}"]
    return "\n".join(lines) + "\n"
