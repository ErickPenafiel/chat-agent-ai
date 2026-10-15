"""Capa 0 — juez LLM sobre conversaciones ya terminadas (inactivas más que el timeout de sesión)."""

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.core.prompt_catalog import PromptStore
from src.db.models import ConversationOutcome
from src.eval.recorder import aware
from src.llm.base import LLMProvider

log = logging.getLogger(__name__)


def format_transcript(transcript: list[dict]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in transcript)


def parse_verdict(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group(0)) if m else {}
    score = float(data["score"])
    if not 1 <= score <= 5:
        raise ValueError(f"score fuera de rango: {score}")
    issues = [i for i in data.get("issues", []) if isinstance(i, dict)]
    return {"score": score, "resolved": bool(data.get("resolved")), "issues": issues}


def judge_outcome(db: Session, llm: LLMProvider, prompts: PromptStore, outcome: ConversationOutcome) -> bool:
    """True si quedó juzgada. Un fallo del LLM o una salida inválida la deja pendiente para el próximo intento."""
    user = f"<conversation>\n{format_transcript(outcome.transcript)}\n</conversation>"
    try:
        v = parse_verdict(llm.complete(prompts.get("judge"), user, json_mode=True))
    except Exception:
        log.exception("el juez falló en la conversación %s", outcome.id)
        return False
    outcome.judge_score, outcome.judge_resolved, outcome.judge_issues = v["score"], v["resolved"], v["issues"]
    outcome.judged_at = datetime.now(timezone.utc)
    db.commit()
    return True


def evaluate_pending(
    session_factory: sessionmaker[Session], llm: LLMProvider, prompts: PromptStore,
    idle_minutes: int, limit: int = 100,
) -> dict:
    """Juzga las conversaciones live inactivas. Simulaciones y replays se juzgan al terminar, no aquí."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
    done = failed = 0
    with session_factory() as db:
        q = select(ConversationOutcome).where(
            ConversationOutcome.judged_at.is_(None), ConversationOutcome.source == "live"
        ).order_by(ConversationOutcome.id).limit(limit)
        for o in db.scalars(q).all():
            if aware(o.updated_at) > cutoff:
                continue
            if judge_outcome(db, llm, prompts, o):
                done += 1
            else:
                failed += 1
    return {"judged": done, "failed": failed}
