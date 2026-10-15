"""Prompts versionados en base de datos: el código trae defaults, lo servido sale de aquí."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Prompt, PromptVersion


def seed(db: Session, defaults: dict[str, str]) -> list[str]:
    """Inserta la versión 1 de los slugs que faltan. Nunca pisa lo que ya existe/editado."""
    created = []
    for slug, text in defaults.items():
        if db.get(Prompt, slug) is None:
            db.add(Prompt(slug=slug, active_version=1))
            db.flush()
            db.add(PromptVersion(slug=slug, version=1, text=text, author="seed"))
            created.append(slug)
    db.commit()
    return created


def get_active(db: Session, slug: str) -> PromptVersion | None:
    p = db.get(Prompt, slug)
    if p is None:
        return None
    return db.scalar(
        select(PromptVersion).where(PromptVersion.slug == slug, PromptVersion.version == p.active_version)
    )


def list_versions(db: Session, slug: str) -> list[PromptVersion]:
    return list(db.scalars(select(PromptVersion).where(PromptVersion.slug == slug).order_by(PromptVersion.version)))


def set_prompt(db: Session, slug: str, text: str, author: str | None = "api", note: str | None = None) -> PromptVersion:
    """Crea una versión nueva y la activa."""
    p = db.get(Prompt, slug)
    if p is None:
        p = Prompt(slug=slug, active_version=0)
        db.add(p)
        db.flush()
    last = max((v.version for v in list_versions(db, slug)), default=0)
    v = PromptVersion(slug=slug, version=last + 1, text=text, author=author, note=note)
    db.add(v)
    p.active_version = last + 1
    db.commit()
    return v


def rollback(db: Session, slug: str, version: int, author: str | None = "api") -> PromptVersion:
    """Reactiva el texto de una versión anterior como versión nueva (historial intacto)."""
    old = next((v for v in list_versions(db, slug) if v.version == version), None)
    if old is None:
        raise ValueError(f"versión {version} no existe para {slug!r}")
    return set_prompt(db, slug, old.text, author, f"rollback a v{version}")
