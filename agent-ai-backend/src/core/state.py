from typing import Any, TypedDict


class ConversationState(TypedDict, total=False):
    # entrada
    channel: str
    user_id: str
    media: list[dict[str, Any]]
    last_user_message: str
    # historial [{"role": "user"|"assistant", "content": str}]
    messages: list[dict[str, str]]
    # nodos
    transcript: str | None  # salida de media_node
    entity: dict[str, Any] | None  # salida de identity_node
    intent: str
    detected_issue: str | None  # sub-clasificación dentro de la intención; dispara conectores
    # captura de datos: valores ya recolectados y campo que se está esperando
    capture: dict[str, str]
    awaiting_capture_field: str | None
    capture_prompt: str | None
    pending_question: str | None  # pregunta original si la captura va antes
    capture_done: bool  # este turno se completó la captura
    answer_pending: bool  # tras completar la captura hay que responder pending_question
    question: str  # consulta del cliente que hay que responder (original o la pendiente)
    connector_results: list[dict[str, Any]]
    # recuperación (RAG)
    retrieved: list[dict[str, Any]]
    # fan-in hacia response_node
    response_parts: list[str]
    reply: str
    reply_mode: str  # llm | llm_error | raw | fallback
    handoff: bool
    # verificación anti-alucinación: supported | rejected | skipped | error (None si está desactivada)
    verification: str | None
    unsupported_claims: list[str]
