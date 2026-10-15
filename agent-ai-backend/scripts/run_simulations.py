"""Capa 0.5: corre escenarios IA-vs-IA contra el agente actual.
Uso: uv run python -m scripts.run_simulations [config/scenarios.yaml]"""

import sys

from scripts._ctx import load_app
from src.eval.simulation import load_scenarios, run_scenario


def main() -> None:
    app = load_app()
    st = app.state
    path = sys.argv[1] if len(sys.argv) > 1 else "config/scenarios.yaml"
    for sc in load_scenarios(path):
        oid = run_scenario(st.graph, st.llm, st.prompts, st.recorder, st.session_factory, sc)
        print(f"{sc.id}: outcome #{oid}")


if __name__ == "__main__":
    main()
