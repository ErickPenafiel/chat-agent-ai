from collections.abc import Callable

from src.core.config import TenantConfig
from src.core.intents import normalize_intent
from src.core.state import ConversationState
from src.nodes.capture import answering_capture

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
        text = state.get("transcript") or state["last_user_message"]
        answering = answering_capture(state) and state.get("intent")
        result = classifier(text, enabled)
        # Si estamos esperando un dato de captura, la respuesta ("Ana") no es una intención nueva;
        # lo único que la interrumpe es pedir una persona («Quiero hablar con alguien»).
        if answering:
            wanted = normalize_intent(result[0] if isinstance(result, tuple) else result)
            if wanted != "escalate" or "escalate" not in config.intents:
                return {"intent": state["intent"], "detected_issue": state.get("detected_issue")}
        intent, issue = result if isinstance(result, tuple) else (result, state.get("detected_issue"))
        intent = normalize_intent(intent)
        # Una intención/issue fuera de config no debe romper el grafo.
        if intent not in config.intents:
            intent = "chat"
        if issue not in valid_issues:
            issue = None
        return {"intent": intent, "detected_issue": issue, "question": text}

    return intent_node
