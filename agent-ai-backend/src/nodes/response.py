"""Fan-in: junta lo que dejaron los nodos anteriores (marcadores en el estado) y redacta la respuesta.

Con LLM: un prompt por marcador (handoff, datos de conectores, KB, charla) más el tono compartido.
Sin LLM, o si el LLM falla: respuesta en crudo con lo que dejaron los nodos.
"""

import json
import logging

from src.connectors.registry import ConnectorRegistry
from src.core.config import TenantConfig
from src.core.prompt_catalog import PromptStore
from src.core.state import ConversationState
from src.llm.base import LLMProvider

log = logging.getLogger(__name__)

FALLBACK = "No tengo información para responder eso por ahora."
CAPTURE_DONE_FALLBACK = "Gracias, ya registré sus datos."
HISTORY_TURNS = 6  # mensajes previos que se le dan al LLM


def _raw_reply(state: ConversationState) -> str:
    parts = list(state.get("response_parts", []))
    if state.get("capture_prompt"):
        parts.append(state["capture_prompt"])
    if not parts and state.get("capture_done"):
        return CAPTURE_DONE_FALLBACK
    return "\n\n".join(parts) if parts else FALLBACK


def _kb_context(blocks: list[dict]) -> str:
    out = []
    for b in blocks:
        text = f"## {b.get('title', '')}\n{b['content']}"
        steps = b.get("steps") or []
        if steps:
            text += "\nPasos:\n" + "\n".join(f"{i}. {s['text']}" for i, s in enumerate(steps, 1))
        out.append(text)
    return "\n\n".join(out)


def _turn_instructions(config: TenantConfig, state: ConversationState, has_context: bool) -> str:
    lines = []
    field = state.get("awaiting_capture_field")
    if state.get("capture_prompt") and field:
        if state.get("pending_question") and not has_context:
            lines.append(
                f"Aún no respondas la consulta del cliente: primero necesitas su dato «{field}». "
                "Pídeselo con amabilidad y dile que enseguida lo ayudas con su consulta."
            )
        else:
            lines.append(f"Al final de tu respuesta, pide con naturalidad el dato «{field}» del cliente.")
    if state.get("capture_done"):
        lines.append("El cliente acaba de dar sus últimos datos: agradécele.")
    if state.get("answer_pending"):
        lines.append("Ya tienes los datos del cliente: ahora responde la consulta que dejó pendiente.")
    return "\n".join(lines)


def make_response_node(
    config: TenantConfig | None = None,
    registry: ConnectorRegistry | None = None,
    llm: LLMProvider | None = None,
    prompts: PromptStore | None = None,
):
    def llm_reply(state: ConversationState) -> str:
        found = [r for r in state.get("connector_results", []) if r["found"]]
        system = [prompts.get("tone")]
        if state.get("handoff"):
            system.append(prompts.get("handoff"))
        else:
            system.append(prompts.get(f"agent_{state['intent']}"))
            system.extend(prompts.get(r["prompt_key"]) for r in found)

        blocks = state.get("retrieved", [])
        history = state.get("messages", [])[-HISTORY_TURNS:]
        question = state.get("question") or state["last_user_message"]
        user = []
        if history:
            user.append("<history>\n" + "\n".join(f"{m['role']}: {m['content']}" for m in history) + "\n</history>")
        if blocks:
            user.append(f"<kb_context>\n{_kb_context(blocks)}\n</kb_context>")
        for r in found:
            user.append(f'<system_data id="{r["id"]}">\n{json.dumps(r["data"], ensure_ascii=False)}\n</system_data>')
        user.append(f"<customer_message>\n{question}\n</customer_message>")
        instr = _turn_instructions(config, state, has_context=bool(blocks or found))
        if instr:
            user.append(f"<turn_instructions>\n{instr}\n</turn_instructions>")
        reply = llm.complete("\n\n".join(system), "\n\n".join(user)).strip()
        if not reply:
            raise ValueError("respuesta vacía del LLM")
        return reply

    def response_node(state: ConversationState) -> dict:
        reply, mode = None, "llm"
        if llm is not None and prompts is not None:
            try:
                reply = llm_reply(state)
            except Exception:
                log.exception("falló la generación con LLM; se responde en crudo")
                mode = "llm_error"
        else:
            mode = "raw"
        if reply is None:
            reply = _raw_reply(state)
            if reply == FALLBACK:
                mode = "fallback"
        messages = list(state.get("messages", []))
        messages.append({"role": "user", "content": state["last_user_message"]})
        messages.append({"role": "assistant", "content": reply})
        return {"reply": reply, "reply_mode": mode, "messages": messages}

    return response_node
