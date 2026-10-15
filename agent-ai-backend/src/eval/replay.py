"""Replay: re-corre conversaciones pasadas (historial de un canal) contra el agente actual para ver el efecto de cambios."""

import uuid

from sqlalchemy.orm import Session, sessionmaker

from src.channels.base import InboundEvent, MessagingChannel
from src.core.dispatcher import turn_input
from src.core.prompt_catalog import PromptStore
from src.db.models import ConversationOutcome
from src.eval.judge import judge_outcome
from src.eval.recorder import OutcomeRecorder
from src.llm.base import LLMProvider


def replay_user(
    graph, channel: MessagingChannel, user_id: str, recorder: OutcomeRecorder,
    session_factory: sessionmaker[Session], llm: LLMProvider | None = None, prompts: PromptStore | None = None,
) -> int | None:
    """Reenvía los mensajes del cliente (no las respuestas viejas) al grafo actual. source=replay."""
    history = channel.fetch_history(user_id)  # NotImplementedError si el canal no expone historial
    user_msgs = [m["text"] for m in history if m["role"] == "user"]
    if not user_msgs:
        return None
    rid = f"replay-{user_id}-{uuid.uuid4().hex[:8]}"
    thread_id = f"replay:{rid}"
    outcome_id = None
    for n, text in enumerate(user_msgs):
        out = graph.invoke(turn_input(InboundEvent("replay", rid, f"{rid}-{n}", text)),
                           {"configurable": {"thread_id": thread_id}})
        outcome_id = recorder.record_turn(thread_id, channel.name, rid, text, out, source="replay")
    if llm and prompts:
        with session_factory() as db:
            judge_outcome(db, llm, prompts, db.get(ConversationOutcome, outcome_id))
    return outcome_id
