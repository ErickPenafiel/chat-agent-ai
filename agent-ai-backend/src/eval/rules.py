"""Capa 0 — reglas deterministas. Baratas: corren en cada turno, sin LLM."""

MAX_TURNS = 15


def evaluate_rules(transcript: list[dict], reply_modes: list[str], handoff: bool) -> list[str]:
    flags = []
    replies = [m["content"] for m in transcript if m["role"] == "assistant"]
    if any(not r.strip() for r in replies):
        flags.append("empty_reply")
    if "fallback" in reply_modes:
        flags.append("fallback_reply")  # el agente no tuvo nada que decir
    if "llm_error" in reply_modes:
        flags.append("degraded_reply")  # el LLM falló y se respondió en crudo
    if any(a == b for a, b in zip(replies, replies[1:])):
        flags.append("repeated_reply")
    if handoff:
        flags.append("handoff")
    if len(replies) > MAX_TURNS:
        flags.append("long_conversation")
    return flags
