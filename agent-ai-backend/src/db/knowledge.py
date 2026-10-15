"""Servicio de KB: validación contra el tenant, versionado y estados."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import TenantConfig
from src.core.intents import normalize_intent
from src.db.models import STATUSES, KnowledgeBlock, KnowledgeBlockVersion

_SNAPSHOT_FIELDS = (
    "title", "content", "intents", "category", "language", "status",
    "keywords", "example_questions", "attachments", "steps", "meta",
)


class InvalidBlock(ValueError):
    pass


@dataclass(frozen=True)
class KBRules:
    intents: frozenset[str]
    categories: frozenset[str]
    language: str

    @classmethod
    def from_config(cls, config: TenantConfig) -> "KBRules":
        return cls(frozenset(config.intents), frozenset(config.categories), config.tone.language)

    def validate(self, data: dict) -> dict:
        """Normaliza y valida los campos presentes; devuelve una copia."""
        data = dict(data)
        if "intents" in data:
            intents = [normalize_intent(i) for i in data["intents"]]
            if not intents:
                raise InvalidBlock("intents no puede estar vacío")
            bad = [i for i in intents if i not in self.intents]
            if bad:
                raise InvalidBlock(f"intents fuera de la config del tenant: {bad}; válidas: {sorted(self.intents)}")
            data["intents"] = list(dict.fromkeys(intents))
        if data.get("category") is not None:
            cat = normalize_intent(data["category"])
            if cat not in self.categories:
                raise InvalidBlock(f"category {cat!r} fuera de la config del tenant; válidas: {sorted(self.categories)}")
            data["category"] = cat
        if "status" in data and data["status"] not in STATUSES:
            raise InvalidBlock(f"status inválido: {data['status']!r}")
        return data


def _snapshot(block: KnowledgeBlock) -> dict:
    return {f: getattr(block, f) for f in _SNAPSHOT_FIELDS}


def _record_version(db: Session, block: KnowledgeBlock, author: str | None, note: str | None) -> None:
    db.add(KnowledgeBlockVersion(
        block_id=block.id, version=block.version, snapshot=_snapshot(block), author=author, note=note
    ))


def create_block(db: Session, rules: KBRules, data: dict, author: str | None = "api") -> KnowledgeBlock:
    data = rules.validate(data)
    data.setdefault("language", rules.language)
    block = KnowledgeBlock(**data, version=1)
    db.add(block)
    db.flush()
    _record_version(db, block, author, None)
    db.commit()
    return block


def update_block(
    db: Session, rules: KBRules, block: KnowledgeBlock, data: dict,
    author: str | None = "api", note: str | None = None,
) -> KnowledgeBlock:
    data = rules.validate(data)
    for k, v in data.items():
        setattr(block, k, v)
    block.version += 1
    _record_version(db, block, author, note)
    db.commit()
    return block


def list_versions(db: Session, block_id: int) -> list[KnowledgeBlockVersion]:
    return list(db.scalars(
        select(KnowledgeBlockVersion).where(KnowledgeBlockVersion.block_id == block_id)
        .order_by(KnowledgeBlockVersion.version)
    ))


def rollback(db: Session, rules: KBRules, block: KnowledgeBlock, version: int, author: str | None = "api") -> KnowledgeBlock:
    """Restaura un snapshot como una versión nueva (el historial no se reescribe)."""
    row = next((v for v in list_versions(db, block.id) if v.version == version), None)
    if row is None:
        raise InvalidBlock(f"versión {version} no existe")
    # Se revalida: el tenant pudo cambiar su config desde que se tomó el snapshot.
    return update_block(db, rules, block, dict(row.snapshot), author, f"rollback a v{version}")


def list_blocks(
    db: Session, intent: str | None = None, category: str | None = None,
    status: str | None = None, language: str | None = None,
) -> list[KnowledgeBlock]:
    q = select(KnowledgeBlock).order_by(KnowledgeBlock.id)
    if category:
        q = q.where(KnowledgeBlock.category == normalize_intent(category))
    if status:
        q = q.where(KnowledgeBlock.status == status)
    if language:
        q = q.where(KnowledgeBlock.language == language)
    blocks = list(db.scalars(q))
    if intent:  # intents es una lista JSON; la KB es chica, se filtra en Python
        intent = normalize_intent(intent)
        blocks = [b for b in blocks if intent in b.intents]
    return blocks


def find_orphans(db: Session, rules: KBRules) -> list[tuple[KnowledgeBlock, list[str]]]:
    """Bloques cuyas intenciones/categoría ya no existen en tenant.yaml."""
    out = []
    for b in list_blocks(db):
        problems = [f"intent:{i}" for i in b.intents if i not in rules.intents]
        if b.category and b.category not in rules.categories:
            problems.append(f"category:{b.category}")
        if problems:
            out.append((b, problems))
    return out
