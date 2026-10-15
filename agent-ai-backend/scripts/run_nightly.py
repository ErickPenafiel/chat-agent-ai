"""Corrida nocturna (cron): juzga conversaciones terminadas y propone mejoras (capas 0 y 2).
Uso: uv run python -m scripts.run_nightly"""

from scripts._ctx import load_app
from src.db.knowledge import KBRules
from src.eval.corrector import propose_improvements
from src.eval.judge import evaluate_pending


def main() -> None:
    app = load_app()
    st = app.state
    judged = evaluate_pending(st.session_factory, st.llm, st.prompts, st.config.thresholds.session_timeout_minutes)
    print("juez:", judged)
    print("corrector:", propose_improvements(st.session_factory, st.llm, st.prompts, KBRules.from_config(st.config)))


if __name__ == "__main__":
    main()
