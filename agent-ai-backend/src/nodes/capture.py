"""Captura de datos genérica: lista de campos por intención, definida en config."""

from src.core.config import TenantConfig
from src.core.state import ConversationState


def _next_missing(fields: list[str], captured: dict[str, str]) -> str | None:
    return next((f for f in fields if f not in captured), None)


def make_capture_node(config: TenantConfig):
    def capture_node(state: ConversationState) -> dict:
        intent = state["intent"]
        fields = config.intents[intent].capture_fields
        captured = dict(state.get("capture", {}))

        awaiting = state.get("awaiting_capture_field")
        if awaiting:
            captured[awaiting] = state["last_user_message"].strip()

        missing = _next_missing(fields, captured)
        update: dict = {
            "capture": captured,
            "awaiting_capture_field": missing,
            # Texto de respaldo (sin LLM); con LLM el response_node redacta la pregunta según el tono.
            "capture_prompt": f"¿Me indica su {missing}?" if missing else None,
            "capture_done": bool(awaiting and not missing),
        }
        if config.intents[intent].capture_before_answer and missing and not awaiting:
            # La captura va antes: la pregunta original queda guardada para responderla al terminar.
            update["pending_question"] = state["last_user_message"]
        if not missing and state.get("pending_question"):
            update["question"] = state["pending_question"]
            update["pending_question"] = None
            update["answer_pending"] = True
        else:
            update["answer_pending"] = False
        return update

    return capture_node
