"""Retriever léxico simple sobre la KB. Un embedding/vector store lo puede reemplazar sin tocar el grafo."""

import re

from sqlalchemy.orm import Session, sessionmaker

from src.db.knowledge import list_blocks
from src.nodes.retrieval import Retriever


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"\w+", text.lower()) if len(t) > 2}


def make_kb_retriever(
    session_factory: sessionmaker[Session], top_k: int = 3, language: str | None = None
) -> Retriever:
    def retrieve(query: str, intent: str) -> list[dict]:
        q = _tokens(query)
        with session_factory() as db:
            scored = []
            # Solo contenido publicado: borradores y archivados nunca llegan al cliente.
            for b in list_blocks(db, intent=intent, status="published", language=language):
                body = _tokens(f"{b.title} {b.content}")
                # Keywords y preguntas de ejemplo pesan más que el cuerpo.
                hints = _tokens(" ".join(b.keywords + b.example_questions))
                score = len(q & body) + 2 * len(q & hints)
                if score:
                    scored.append((score, b))
        scored.sort(key=lambda x: -x[0])
        return [
            {"id": b.id, "title": b.title, "content": b.content,
             "attachments": b.attachments, "steps": b.steps}
            for _, b in scored[:top_k]
        ]

    return retrieve
