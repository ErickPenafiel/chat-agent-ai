from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.core.prompt_catalog import KNOWN_VARIABLES, PromptStore, unknown_variables
from src.db import prompts as prompts_db

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    note: str | None = None


class PromptOut(BaseModel):
    slug: str
    version: int
    text: str


class VersionOut(BaseModel):
    version: int
    author: str | None
    note: str | None
    created_at: datetime
    text: str


def _store(request: Request) -> PromptStore:
    return request.app.state.prompts


def _known(request: Request, slug: str) -> PromptStore:
    store = _store(request)
    if slug not in store.defaults:
        raise HTTPException(404, f"prompt {slug!r} no existe en este despliegue; válidos: {sorted(store.defaults)}")
    return store


def _out(slug: str, v) -> PromptOut:
    return PromptOut(slug=slug, version=v.version, text=v.text)


@router.get("", response_model=list[PromptOut])
def list_prompts(request: Request):
    store = _store(request)
    with store._sf() as db:
        return [_out(s, prompts_db.get_active(db, s)) for s in sorted(store.defaults)]


@router.get("/{slug}", response_model=PromptOut)
def get_prompt(slug: str, request: Request):
    store = _known(request, slug)
    with store._sf() as db:
        return _out(slug, prompts_db.get_active(db, slug))


@router.get("/{slug}/versions", response_model=list[VersionOut])
def versions(slug: str, request: Request):
    store = _known(request, slug)
    with store._sf() as db:
        return prompts_db.list_versions(db, slug)


@router.put("/{slug}", response_model=PromptOut)
def update(slug: str, body: PromptUpdate, request: Request):
    store = _known(request, slug)
    bad = unknown_variables(body.text)
    if bad:
        raise HTTPException(422, f"variables desconocidas: {sorted(bad)}; válidas: {sorted(KNOWN_VARIABLES)}")
    with store._sf() as db:
        return _out(slug, prompts_db.set_prompt(db, slug, body.text, note=body.note))


@router.post("/{slug}/rollback/{version}", response_model=PromptOut)
def rollback(slug: str, version: int, request: Request):
    store = _known(request, slug)
    with store._sf() as db:
        try:
            return _out(slug, prompts_db.rollback(db, slug, version))
        except ValueError as e:
            raise HTTPException(422, str(e))
