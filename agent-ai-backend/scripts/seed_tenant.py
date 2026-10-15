"""Primer arranque de un tenant: valida tenant.yaml, siembra los prompts y (opcional) carga la KB inicial.
Solo carga la KB si está vacía, para no pisar nada. Para sincronizar después, usar rebuild_knowledge_base.

Uso: uv run python -m scripts.seed_tenant [archivo_kb.yaml]
Requiere el esquema creado antes: uv run alembic upgrade head"""

import sys

from sqlalchemy import func, select

from src.api.app import create_app
from src.db.kb_loader import load_kb_file, sync_blocks
from src.db.knowledge import KBRules
from src.db.models import KnowledgeBlock


def main() -> None:
    kb_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = create_app()  # valida tenant.yaml y siembra los prompts que falten
    st = app.state
    print(f"tenant: {st.config.business_name}")
    print(f"prompts: {len(st.prompts.defaults)} disponibles")
    if kb_path is None:
        print("KB: vacía (no se indicó archivo). Cada despliegue carga la suya.")
        return
    with st.session_factory() as db:
        if db.scalar(select(func.count()).select_from(KnowledgeBlock)):
            raise SystemExit("la KB ya tiene bloques; usa scripts.rebuild_knowledge_base para sincronizar")
        print("KB:", sync_blocks(db, KBRules.from_config(st.config), load_kb_file(kb_path)))


if __name__ == "__main__":
    main()
