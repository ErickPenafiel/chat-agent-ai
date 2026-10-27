"""Capa 2 — corrector: de las conversaciones malas propone diffs de KB/prompts. Nunca aplica solo."""

import json
import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.core.prompt_catalog import PROTECTED_PROMPTS, PromptStore, unknown_variables
from src.db import knowledge
from src.db import prompts as prompts_db
from src.db.knowledge import InvalidBlock, KBRules
from src.db.models import ConversationOutcome, ImprovementProposal, KnowledgeBlock
from src.eval.judge import format_transcript
from src.llm.base import LLMProvider

log = logging.getLogger(__name__)

KB_EDITABLE = ("title", "content", "keywords", "example_questions")
MAX_OUTCOMES = 20
MAX_KB_BLOCKS = 40
KB_SNIPPET = 600


class Conflict(Exception):
    """El objetivo cambió desde que se hizo la propuesta."""


SCAN_RECENT = 500


def _is_bad(o: ConversationOutcome) -> bool:
    return (
        (o.judge_score is not None and o.judge_score <= 3)
        or (o.feedback_rating is not None and o.feedback_rating <= 2)
        or "fallback_reply" in o.rule_flags
    )


def select_bad_outcomes(db: Session, limit: int = MAX_OUTCOMES) -> list[ConversationOutcome]:
    """Las peores primero. rule_flags es JSON, así que ese filtro se hace en Python sobre las recientes."""
    recent = db.scalars(
        select(ConversationOutcome).where(ConversationOutcome.corrected_at.is_(None))
        .order_by(ConversationOutcome.id.desc()).limit(SCAN_RECENT)
    )
    bad = [o for o in recent if _is_bad(o)]
    bad.sort(key=lambda o: (o.judge_score if o.judge_score is not None else 99, o.id))
    return bad[:limit]


def _context(db: Session, prompts: PromptStore) -> str:
    kb = [
        {"id": b.id, "title": b.title, "intents": b.intents, "content": b.content[:KB_SNIPPET]}
        for b in knowledge.list_blocks(db, status="published")[:MAX_KB_BLOCKS]
    ]
    pr = {s: prompts.raw(s) for s in sorted(prompts.defaults) if s not in PROTECTED_PROMPTS}
    return f"<current_prompts>\n{json.dumps(pr, ensure_ascii=False)}\n</current_prompts>\n" \
           f"<current_kb>\n{json.dumps(kb, ensure_ascii=False)}\n</current_kb>"


def _validate(db: Session, rules: KBRules, prompts: PromptStore, p: dict) -> tuple[str, dict, dict | None]:
    """Devuelve (kind, payload, before) o lanza ValueError si la propuesta no es aplicable."""
    kind = p.get("kind")
    if kind == "kb_create":
        data = {k: p[k] for k in ("title", "content", "intents", "category", "keywords", "example_questions") if p.get(k) is not None}
        if not data.get("title") or not data.get("content"):
            raise ValueError("kb_create sin título o contenido")
        try:
            data = rules.validate(data)
        except InvalidBlock as e:
            raise ValueError(str(e))
        return kind, data, None
    if kind == "kb_update":
        block = db.get(KnowledgeBlock, p.get("block_id"))
        fields = p.get("fields") or {}
        if block is None or not fields or set(fields) - set(KB_EDITABLE):
            raise ValueError("kb_update con bloque inexistente o campos no permitidos")
        return kind, {"block_id": block.id, "fields": fields}, {f: getattr(block, f) for f in fields}
    if kind == "prompt_update":
        slug, text = p.get("slug"), p.get("text")
        if slug not in prompts.defaults or slug in PROTECTED_PROMPTS:
            raise ValueError(f"slug no editable por el corrector: {slug!r}")
        if not text or unknown_variables(text):
            raise ValueError("texto vacío o con variables desconocidas")
        return kind, {"slug": slug, "text": text}, {"text": prompts.raw(slug)}
    raise ValueError(f"kind desconocido: {kind!r}")


def propose_improvements(
    session_factory: sessionmaker[Session], llm: LLMProvider, prompts: PromptStore, rules: KBRules,
) -> dict:
    with session_factory() as db:
        outcomes = select_bad_outcomes(db)
        if not outcomes:
            return {"outcomes": 0, "proposals": 0, "discarded": 0}
        convs = "\n\n".join(
            f'<conversation id="{o.id}" score="{o.judge_score}" feedback="{o.feedback_rating}" '
            f'flags="{",".join(o.rule_flags)}" issues="{json.dumps(o.judge_issues, ensure_ascii=False)}">\n'
            f"{format_transcript(o.transcript)}\n</conversation>"
            for o in outcomes
        )
        user = f"{_context(db, prompts)}\n\n{convs}"
        try:
            raw = llm.complete(prompts.get("corrector"), user, json_mode=True)
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            items = json.loads(m.group(0)).get("proposals", []) if m else []
        except Exception:
            log.exception("el corrector falló; las conversaciones quedan para el próximo intento")
            return {"outcomes": len(outcomes), "proposals": 0, "discarded": 0, "error": True}

        valid_ids = {o.id for o in outcomes}
        created = discarded = 0
        for p in items if isinstance(items, list) else []:
            try:
                kind, payload, before = _validate(db, rules, prompts, p)
            except (ValueError, TypeError, AttributeError) as e:
                log.warning("propuesta descartada: %s", e)
                discarded += 1
                continue
            evidence = [i for i in p.get("evidence", []) if i in valid_ids]
            db.add(ImprovementProposal(
                kind=kind, payload=payload, before=before,
                rationale=str(p.get("rationale", "")), evidence_outcome_ids=evidence,
            ))
            created += 1
        now = datetime.now(UTC)
        for o in outcomes:
            o.corrected_at = now
        db.commit()
        return {"outcomes": len(outcomes), "proposals": created, "discarded": discarded}


def apply_proposal(
    db: Session, proposal: ImprovementProposal, rules: KBRules, prompts: PromptStore,
) -> None:
    """Aprobación humana: aplica con versionado (autor «corrector»), por lo que se puede revertir."""
    pl = proposal.payload
    note = f"propuesta #{proposal.id}: {proposal.rationale}"[:500]
    if proposal.kind == "kb_create":
        knowledge.create_block(db, rules, dict(pl), author="corrector")
    elif proposal.kind == "kb_update":
        block = db.get(KnowledgeBlock, pl["block_id"])
        if block is None or any(getattr(block, f) != v for f, v in (proposal.before or {}).items()):
            raise Conflict("el bloque cambió o ya no existe desde que se hizo la propuesta")
        knowledge.update_block(db, rules, block, dict(pl["fields"]), author="corrector", note=note)
    elif proposal.kind == "prompt_update":
        if prompts.raw(pl["slug"]) != (proposal.before or {}).get("text"):
            raise Conflict("el prompt cambió desde que se hizo la propuesta")
        prompts_db.set_prompt(db, pl["slug"], pl["text"], author="corrector", note=note)
    proposal.status = "approved"
    proposal.resolved_at = datetime.now(UTC)
    db.commit()
