from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.knowledge_blocks import get_db, get_rules
from src.db import knowledge
from src.db.knowledge import KBRules
from src.db.models import ConversationOutcome, ImprovementProposal
from src.eval.corrector import Conflict, apply_proposal

outcomes_router = APIRouter(prefix="/conversation-outcomes", tags=["evaluation"])
proposals_router = APIRouter(prefix="/improvement-proposals", tags=["evaluation"])


class OutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    thread_id: str
    channel: str
    user_id: str
    source: str
    scenario: str | None
    transcript: list[dict[str, Any]]
    turns: int
    intent: str | None
    handoff: bool
    rule_flags: list[str]
    judge_score: float | None
    judge_resolved: bool | None
    judge_issues: list[dict[str, Any]]
    feedback_rating: int | None
    feedback_comment: str | None
    created_at: datetime
    updated_at: datetime


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    status: str
    payload: dict[str, Any]
    before: dict[str, Any] | None
    rationale: str
    evidence_outcome_ids: list[int]
    created_at: datetime
    resolved_at: datetime | None


@outcomes_router.get("", response_model=list[OutcomeOut])
def list_outcomes(
    source: str | None = None, flag: str | None = None, max_score: float | None = None,
    limit: int = 100, db: Session = Depends(get_db),
):
    q = select(ConversationOutcome).order_by(ConversationOutcome.id.desc()).limit(min(limit, 500))
    if source:
        q = q.where(ConversationOutcome.source == source)
    if max_score is not None:
        q = q.where(ConversationOutcome.judge_score <= max_score)
    rows = list(db.scalars(q))
    return [o for o in rows if flag in o.rule_flags] if flag else rows


@outcomes_router.post("/feedback")
def feedback(body: Feedback, request: Request):
    """Capa 1: el cliente califica su última conversación."""
    oid = request.app.state.recorder.record_feedback(body.channel, body.user_id, body.rating, body.comment)
    if oid is None:
        raise HTTPException(404, "no hay conversación para ese cliente")
    return {"outcome_id": oid}


@outcomes_router.get("/{outcome_id}", response_model=OutcomeOut)
def get_outcome(outcome_id: int, db: Session = Depends(get_db)):
    o = db.get(ConversationOutcome, outcome_id)
    if not o:
        raise HTTPException(404, "conversación no encontrada")
    return o


def _proposal(db: Session, pid: int) -> ImprovementProposal:
    p = db.get(ImprovementProposal, pid)
    if not p:
        raise HTTPException(404, "propuesta no encontrada")
    return p


@proposals_router.get("", response_model=list[ProposalOut])
def list_proposals(status: str | None = None, db: Session = Depends(get_db)):
    q = select(ImprovementProposal).order_by(ImprovementProposal.id.desc())
    if status:
        q = q.where(ImprovementProposal.status == status)
    return list(db.scalars(q))


@proposals_router.get("/{pid}", response_model=ProposalOut)
def get_proposal(pid: int, db: Session = Depends(get_db)):
    return _proposal(db, pid)


@proposals_router.post("/{pid}/approve", response_model=ProposalOut)
def approve(pid: int, request: Request, db: Session = Depends(get_db), rules: KBRules = Depends(get_rules)):
    p = _proposal(db, pid)
    if p.status != "pending":
        raise HTTPException(409, f"la propuesta ya está {p.status}")
    try:
        apply_proposal(db, p, rules, request.app.state.prompts)
    except Conflict as e:
        raise HTTPException(409, str(e))
    except knowledge.InvalidBlock as e:
        raise HTTPException(422, str(e))
    return p


@proposals_router.post("/{pid}/reject", response_model=ProposalOut)
def reject(pid: int, db: Session = Depends(get_db)):

    p = _proposal(db, pid)
    if p.status != "pending":
        raise HTTPException(409, f"la propuesta ya está {p.status}")
    p.status, p.resolved_at = "rejected", datetime.now(UTC)
    db.commit()
    return p
