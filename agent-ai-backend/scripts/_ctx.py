"""Contexto compartido por los scripts: la misma app que corre en producción, sin servidor HTTP."""

from src.api.app import create_app


def load_app():
    app = create_app()
    if app.state.llm is None:
        raise SystemExit("estos scripts necesitan un bloque `llm` en tenant.yaml")
    return app
