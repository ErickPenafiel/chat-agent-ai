"""Carga de KB desde un archivo YAML (fuente de verdad versionable en git). Todo pasa por la validación del tenant."""

from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import KnowledgeBlockCreate
from src.db import knowledge
from src.db.knowledge import KBRules
from src.db.models import KnowledgeBlockVersion

AUTHOR = "seed"
_COMPARED = ("content", "intents", "category", "keywords", "example_questions", "attachments", "steps", "meta", "status")


class KBFileError(ValueError):
    pass


def load_kb_file(path: str | Path) -> list[KnowledgeBlockCreate]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out = []
    for i, raw in enumerate(data.get("blocks", [])):
        try:
            out.append(KnowledgeBlockCreate.model_validate(raw))
        except ValidationError as e:
            raise KBFileError(f"bloque #{i + 1} ({raw.get('title', '?')!r}): {e}") from e
    titles = [b.title for b in out]
    if len(set(titles)) != len(titles):
        raise KBFileError("títulos duplicados en el archivo (se usan para identificar cada bloque)")
    return out


def sync_blocks(db: Session, rules: KBRules, blocks: list[KnowledgeBlockCreate], prune: bool = False) -> dict:
    """Crea los que faltan y actualiza (con versión nueva) los que difieren. Identifica por (título, idioma).
    prune=True archiva —no borra— los bloques de origen «seed» que ya no están en el archivo."""
    existing = {(b.title, b.language): b for b in knowledge.list_blocks(db)}
    stats = {"created": 0, "updated": 0, "unchanged": 0, "archived": 0}
    seen = set()
    for b in blocks:
        data = rules.validate(b.model_dump(exclude_none=True))
        key = (data["title"], data.get("language", rules.language))
        seen.add(key)
        current = existing.get(key)
        if current is None:
            knowledge.create_block(db, rules, data, author=AUTHOR)
            stats["created"] += 1
            continue
        changed = {f: data[f] for f in _COMPARED if f in data and getattr(current, f) != data[f]}
        if changed:
            knowledge.update_block(db, rules, current, changed, author=AUTHOR, note="sync desde archivo")
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    if prune:
        seed_ids = set(db.scalars(
            select(KnowledgeBlockVersion.block_id).where(
                KnowledgeBlockVersion.version == 1, KnowledgeBlockVersion.author == AUTHOR
            )
        ))
        for key, block in existing.items():
            if key not in seen and block.id in seed_ids and block.status != "archived":
                knowledge.update_block(db, rules, block, {"status": "archived"}, author=AUTHOR, note="ausente del archivo")
                stats["archived"] += 1
    return stats
