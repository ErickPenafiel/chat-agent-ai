"""Capa 0.7: corre los casos dorados contra el agente y reporta métricas.
Uso: uv run python -m scripts.run_golden [--only categoria] [--out eval_reports]
Usa una base en memoria con la KB del ejemplo, así que no toca tus datos. Hace llamadas reales al LLM
configurado en el tenant (hacen falta las claves en .env)."""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.api.app import create_app
from src.core.config import load_tenant_config
from src.db.kb_loader import load_kb_file, sync_blocks
from src.db.knowledge import KBRules
from src.eval.golden import load_golden, render_markdown, run_case, score_case, summarize

EX = "examples/coffee-shop"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default=f"{EX}/tenant.yaml")
    ap.add_argument("--kb", default=f"{EX}/kb.yaml")
    ap.add_argument("--golden", default=f"{EX}/golden.yaml")
    ap.add_argument("--only", help="corre solo una categoría")
    ap.add_argument("--out", default="eval_reports")
    ap.add_argument("--pause", type=float, default=1.5, help="segundos entre casos, para no agotar la cuota del LLM")
    ap.add_argument("--retries", type=int, default=3, help="intentos por caso si el LLM devuelve error")
    a = ap.parse_args()

    load_dotenv()
    # Base en memoria y solo en este proceso: el ejemplo trae auth.mode=disabled, que pide este opt-in.
    os.environ.setdefault("ALLOW_INSECURE_AUTH", "1")
    config = load_tenant_config(a.tenant)
    app = create_app(config, "sqlite:///:memory:")
    if app.state.llm is None:
        raise SystemExit("el tenant necesita un bloque `llm` y su clave en .env para evaluar")
    with app.state.session_factory() as db:
        sync_blocks(db, KBRules.from_config(config), load_kb_file(a.kb))

    cases = [c for c in load_golden(a.golden) if not a.only or c.category == a.only]
    results = []
    for i, case in enumerate(cases, 1):
        for attempt in range(1, a.retries + 1):
            r = score_case(case, run_case(app.state.graph, case))
            if not r["invalid"]:
                break
            time.sleep(5 * attempt)  # el error del LLM suele ser un límite de uso: espera y reintenta
        results.append(r)
        state = "DESCARTADO (error del LLM)" if r["invalid"] else ("ok " if r["passed"] else "FALLA")
        print(f"[{i}/{len(cases)}] {state} {case.id}")
        time.sleep(a.pause)

    summary = summarize(cases, results)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / f"golden-{stamp}.json").write_text(
        json.dumps({"config": {"provider": config.llm.provider, "model": config.llm.model}, "summary": summary,
                    "results": results}, ensure_ascii=False, indent=1))
    md = render_markdown(summary, results, f"Casos dorados — {config.business_name} — {config.llm.model}")
    (out / f"golden-{stamp}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
