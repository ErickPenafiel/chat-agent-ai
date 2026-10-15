"""Intenciones base del template. Cada tenant puede ampliarlas desde tenant.yaml."""

BASE_INTENTS = ("support", "sales", "info", "chat", "escalate")

# Intenciones que el grafo necesita para funcionar, siempre deben estar habilitadas.
REQUIRED_INTENTS = ("chat", "escalate")

# Intenciones que se resuelven consultando la KB (RAG).
RETRIEVAL_INTENTS = ("support", "sales", "info")


def normalize_intent(value: str) -> str:
    return value.strip().lower()
