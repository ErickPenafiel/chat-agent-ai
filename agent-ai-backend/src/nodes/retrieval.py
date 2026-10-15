from collections.abc import Callable
from typing import Any

from src.core.state import ConversationState

# (query, intent) -> bloques de KB.
Retriever = Callable[[str, str], list[dict[str, Any]]]


def empty_retriever(query: str, intent: str) -> list[dict[str, Any]]:
    return []


def make_retrieval_node(retriever: Retriever = empty_retriever):
    def retrieval_node(state: ConversationState) -> dict:
        query = state.get("question") or state.get("transcript") or state["last_user_message"]
        blocks = retriever(query, state["intent"])
        parts = list(state.get("response_parts", []))
        parts.extend(b["content"] for b in blocks)
        return {"retrieved": blocks, "response_parts": parts}

    return retrieval_node
