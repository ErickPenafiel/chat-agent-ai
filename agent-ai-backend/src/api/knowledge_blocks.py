from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src.api.schemas import (
    KnowledgeBlockCreate,
    KnowledgeBlockOut,
    KnowledgeBlockUpdate,
    OrphanOut,
    VersionOut,
    _check_steps,
)
from src.db import knowledge
from src.db.knowledge import KBRules
from src.db.models import KnowledgeBlock

router = APIRouter(prefix="/knowledge-blocks", tags=["knowledge-blocks"])


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


def get_rules(request: Request) -> KBRules:
    return KBRules.from_config(request.app.state.config)


def _get_or_404(db: Session, block_id: int) -> KnowledgeBlock:
    block = db.get(KnowledgeBlock, block_id)
    if not block:
        raise HTTPException(404, "bloque no encontrado")
    return block


@router.post("", response_model=KnowledgeBlockOut, status_code=201)
def create(body: KnowledgeBlockCreate, db: Session = Depends(get_db), rules: KBRules = Depends(get_rules)):
    data = body.model_dump(exclude_none=True)
    try:
        return knowledge.create_block(db, rules, data)
    except knowledge.InvalidBlock as e:
        raise HTTPException(422, str(e))


@router.get("", response_model=list[KnowledgeBlockOut])
def list_(
    intent: str | None = None, category: str | None = None,
    status: str | None = None, language: str | None = None,
    db: Session = Depends(get_db),
):
    return knowledge.list_blocks(db, intent, category, status, language)


@router.get("/orphans", response_model=list[OrphanOut])
def orphans(db: Session = Depends(get_db), rules: KBRules = Depends(get_rules)):
    """Bloques que referencian intenciones/categorías que ya no están en tenant.yaml."""
    return [OrphanOut(id=b.id, title=b.title, problems=p) for b, p in knowledge.find_orphans(db, rules)]


@router.get("/{block_id}", response_model=KnowledgeBlockOut)
def get(block_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, block_id)


@router.patch("/{block_id}", response_model=KnowledgeBlockOut)
def update(block_id: int, body: KnowledgeBlockUpdate, db: Session = Depends(get_db), rules: KBRules = Depends(get_rules)):
    block = _get_or_404(db, block_id)
    data = body.model_dump(exclude_unset=True)
    note = data.pop("note", None)
    if "attachments" in data or "steps" in data:
        # Se valida la combinación final, no solo lo enviado.
        from src.api.schemas import Attachment, Step
        att = body.attachments if body.attachments is not None else [Attachment(**a) for a in block.attachments]
        steps = body.steps if body.steps is not None else [Step(**s) for s in block.steps]
        try:
            _check_steps(att, steps)
        except ValueError as e:
            raise HTTPException(422, str(e))
    try:
        return knowledge.update_block(db, rules, block, data, note=note)
    except knowledge.InvalidBlock as e:
        raise HTTPException(422, str(e))


@router.delete("/{block_id}", status_code=204)
def delete(block_id: int, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, block_id))
    db.commit()
    return Response(status_code=204)


@router.get("/{block_id}/versions", response_model=list[VersionOut])
def versions(block_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, block_id)
    return knowledge.list_versions(db, block_id)


@router.post("/{block_id}/rollback/{version}", response_model=KnowledgeBlockOut)
def rollback(block_id: int, version: int, db: Session = Depends(get_db), rules: KBRules = Depends(get_rules)):
    block = _get_or_404(db, block_id)
    try:
        return knowledge.rollback(db, rules, block, version)
    except knowledge.InvalidBlock as e:
        raise HTTPException(422, str(e))
