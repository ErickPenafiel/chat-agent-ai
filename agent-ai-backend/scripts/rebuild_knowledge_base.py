"""Sincroniza la KB con un archivo YAML (crea/actualiza con versionado; --prune archiva los ausentes de origen seed).
Las ediciones hechas a mano sobre bloques del archivo se sobrescriben (queda la versión anterior para rollback).

Uso: uv run python -m scripts.rebuild_knowledge_base <archivo_kb.yaml> [--prune]"""

import sys

from src.api.app import create_app
from src.db.kb_loader import load_kb_file, sync_blocks
from src.db.knowledge import KBRules


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--prune"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    app = create_app()
    st = app.state
    blocks = load_kb_file(args[0])  # valida el archivo completo antes de tocar la base
    with st.session_factory() as db:
        print(sync_blocks(db, KBRules.from_config(st.config), blocks, prune="--prune" in sys.argv))


if __name__ == "__main__":
    main()
