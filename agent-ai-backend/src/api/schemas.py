from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["draft", "published", "archived"]


class Attachment(BaseModel):
    id: str = Field(min_length=1)
    type: Literal["image", "video", "document", "audio"]
    url: str = Field(min_length=1)
    alt: str | None = None


class Step(BaseModel):
    text: str = Field(min_length=1)
    attachment_id: str | None = None


def _check_steps(attachments: list[Attachment], steps: list[Step]) -> None:
    ids = [a.id for a in attachments]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de attachments duplicados")
    for s in steps:
        if s.attachment_id and s.attachment_id not in ids:
            raise ValueError(f"el paso referencia un attachment inexistente: {s.attachment_id!r}")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeBlockCreate(_Strict):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    intents: list[str] = Field(min_length=1)
    category: str | None = None
    language: str | None = None  # default: idioma del tenant
    status: Status = "published"
    keywords: list[str] = []
    example_questions: list[str] = []
    attachments: list[Attachment] = []
    steps: list[Step] = []
    meta: dict[str, Any] = {}

    @model_validator(mode="after")
    def _steps_ok(self):
        _check_steps(self.attachments, self.steps)
        return self


class KnowledgeBlockUpdate(_Strict):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    intents: list[str] | None = Field(default=None, min_length=1)
    category: str | None = None
    language: str | None = None
    status: Status | None = None
    keywords: list[str] | None = None
    example_questions: list[str] | None = None
    attachments: list[Attachment] | None = None
    steps: list[Step] | None = None
    meta: dict[str, Any] | None = None
    note: str | None = None  # nota para el historial; no se guarda en el bloque


class KnowledgeBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    intents: list[str]
    category: str | None
    language: str
    status: str
    version: int
    keywords: list[str]
    example_questions: list[str]
    attachments: list[Attachment]
    steps: list[Step]
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    author: str | None
    note: str | None
    created_at: datetime
    snapshot: dict[str, Any]


class OrphanOut(BaseModel):
    id: int
    title: str
    problems: list[str]
