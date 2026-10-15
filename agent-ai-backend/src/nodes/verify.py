"""Guardrail anti-alucinación (opcional, `verify_responses` en tenant.yaml).

Un LLM compara el borrador de `response` con la KB y los datos de conectores que lo respaldan. Si afirma algo que
no está ahí, se reemplaza por una respuesta segura. Solo se verifican respuestas con hechos que contrastar.
Ante un fallo del verificador se conserva el borrador (no se bloquea la conversación por una falla del guardrail).
"""

import json
import logging
import re

from src.core.prompt_catalog import PromptStore
from src.core.state import ConversationState
from src.llm.base import LLMProvider
from src.nodes.response import _kb_context

log = logging.getLogger(__name__)

UNSUPPORTED_REPLY = "No tengo información confirmada sobre eso por ahora. ¿Quiere que lo derive con una persona del equipo?"


def _parse(raw: str) -> tuple[bool, list[str]]:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group(0)) if m else {}
    supported = data["supported"]
    if not isinstance(supported, bool):
        raise ValueError("supported no es booleano")
    claims = [c for c in data.get("unsupported_claims", []) if isinstance(c, str)]
    return supported, claims


def make_verify_node(llm: LLMProvider, prompts: PromptStore):
    def verify_node(state: ConversationState) -> dict:
        blocks = state.get("retrieved", [])
        found = [r for r in state.get("connector_results", []) if r["found"]]
        # Sin respuesta del LLM, handoff o hechos que contrastar no hay nada que verificar.
        if state.get("reply_mode") != "llm" or state.get("handoff") or not (blocks or found):
            return {"verification": "skipped"}

        user = []
        if blocks:
            user.append(f"<kb_context>\n{_kb_context(blocks)}\n</kb_context>")
        for r in found:
            user.append(f'<system_data id="{r["id"]}">\n{json.dumps(r["data"], ensure_ascii=False)}\n</system_data>')
        user.append(f"<draft_reply>\n{state['reply']}\n</draft_reply>")
        try:
            supported, claims = _parse(llm.complete(prompts.get("verifier"), "\n\n".join(user), json_mode=True))
        except Exception:
            log.exception("falló la verificación; se envía el borrador")
            return {"verification": "error"}
        if supported:
            return {"verification": "supported"}

        log.warning("respuesta sin respaldo reemplazada. Afirmaciones: %s", claims)
        messages = list(state.get("messages", []))
        if messages and messages[-1].get("role") == "assistant":
            messages[-1] = {"role": "assistant", "content": UNSUPPORTED_REPLY}
        return {
            "verification": "rejected", "unsupported_claims": claims,
            "reply": UNSUPPORTED_REPLY, "messages": messages,
        }

    return verify_node
