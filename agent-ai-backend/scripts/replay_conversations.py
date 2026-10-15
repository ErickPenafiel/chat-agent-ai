"""Re-corre conversaciones pasadas de un canal contra el agente actual.
Uso: uv run python -m scripts.replay_conversations <canal> <user_id> [<user_id> ...]
El canal debe implementar fetch_history (ej. el adapter web; WhatsApp Cloud API no expone historial)."""

import sys

from scripts._ctx import load_app
from src.eval.replay import replay_user


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    app = load_app()
    st = app.state
    channel = st.channels.get(sys.argv[1])
    if channel is None:
        raise SystemExit(f"canal {sys.argv[1]!r} no está activo en tenant.yaml")
    for user_id in sys.argv[2:]:
        oid = replay_user(st.graph, channel, user_id, st.recorder, st.session_factory, st.llm, st.prompts)
        print(f"{user_id}: outcome #{oid}")


if __name__ == "__main__":
    main()
