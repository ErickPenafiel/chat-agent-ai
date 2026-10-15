from collections.abc import Callable

from src.core.config import TenantConfig
from src.core.intents import normalize_intent
from src.core.state import ConversationState

# Clasificador inyectable: (mensaje, intenciones habilitadas) -> intención, o (intención, issue).
Classifier = Callable[[str, list[str]], "str | tuple[str, str | None]"]


def default_classifier(message: str, enabled: list[str]) -> str:
    return "chat"


def make_intent_node(
    config: TenantConfig,
    classifier: Classifier = default_classifier,
    valid_issues: frozenset[str] = frozenset(),
):
    enabled = list(config.intents)

    def intent_node(state: ConversationState) -> dict:
        # Si estamos esperando un dato de captura, la respuesta ("Ana") no es una intención nueva.
        if state.get("awaiting_capture_field") and state.get("intent"):
            return {"intent": state["intent"], "detected_issue": state.get("detected_issue")}

        text = state.get("transcript") or state["last_user_message"]
        result = classifier(text, enabled)
        intent, issue = result if isinstance(result, tuple) else (result, state.get("detected_issue"))
        intent = normalize_intent(intent)
        # Una intención/issue fuera de config no debe romper el grafo.
        if intent not in config.intents:
            intent = "chat"
        if issue not in valid_issues:
            issue = None
        return {"intent": intent, "detected_issue": issue, "question": text}

    return intent_node
