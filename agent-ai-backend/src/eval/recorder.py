"""Registra cada turno en conversation_outcomes (capas 0 y 1)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import ConversationOutcome
from src.eval.rules import evaluate_rules


def aware(dt: datetime) -> datetime:
    """SQLite devuelve datetimes sin zona; se tratan como UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _latest(db: Session, thread_id: str, source: str) -> ConversationOutcome | None:
    return db.scalar(
        select(ConversationOutcome)
        .where(ConversationOutcome.thread_id == thread_id, ConversationOutcome.source == source)
        .order_by(ConversationOutcome.id.desc())
    )


class OutcomeRecorder:
    def __init__(self, session_factory: sessionmaker[Session], session_timeout_minutes: int):
        self._sf = session_factory
        self._timeout = timedelta(minutes=session_timeout_minutes)

    def record_turn(
        self, thread_id: str, channel: str, user_id: str, user_text: str, out: dict,
        source: str = "live", scenario: str | None = None,
    ) -> int:
        """Agrega el turno a la sesión en curso; si pasó el timeout de sesión, abre una conversación nueva."""
        now = datetime.now(UTC)
        with self._sf() as db:
            o = _latest(db, thread_id, source)
            if o is None or now - aware(o.updated_at) > self._timeout:
                o = ConversationOutcome(
                    thread_id=thread_id, channel=channel, user_id=user_id, source=source, scenario=scenario,
                    transcript=[], reply_modes=[], turns=0, handoff=False,
                )
                db.add(o)
            o.transcript = [*o.transcript,
                            {"role": "user", "content": user_text},
                            {"role": "assistant", "content": out["reply"]}]
            o.reply_modes = [*o.reply_modes, out.get("reply_mode", "")]
            o.turns += 1
            o.intent = out.get("intent")
            o.handoff = bool(o.handoff or out.get("handoff"))
            o.rule_flags = evaluate_rules(o.transcript, o.reply_modes, o.handoff)
            o.updated_at = now
            db.commit()
            return o.id

    def record_feedback(self, channel: str, user_id: str, rating: int, comment: str | None = None) -> int | None:
        """Capa 1: el rating se asocia a la conversación live más reciente de ese cliente."""
        with self._sf() as db:
            o = _latest(db, f"{channel}:{user_id}", "live")
            if o is None:
                return None
            o.feedback_rating, o.feedback_comment = rating, comment
            db.commit()
            return o.id
