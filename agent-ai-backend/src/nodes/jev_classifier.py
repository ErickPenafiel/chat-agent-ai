import logging
from collections.abc import Iterable

from src.llm.jev import JevClient
from src.nodes.intent import Classifier

log = logging.getLogger(__name__)

_DEFAULT_DESCRIPTIONS = {
    "support": "El cliente tiene un problema, falla o duda sobre algo que ya compró o usa.",
    "sales": "El cliente quiere comprar, conocer precios, planes o productos.",
    "info": "El cliente pide información general (horarios, ubicación, políticas).",
    "chat": "Saludo, conversación casual o mensaje que no encaja en otra intención.",
    "escalate": "El cliente pide hablar con una persona o está muy molesto.",
}


def make_jev_classifier(
    jev: JevClient,
    descriptions: dict[str, str],
    issues: Iterable[str] = (),
    min_confidence: float = 0.5,
    fallback: Classifier | None = None,
) -> Classifier:
    """Clasifica con una sola llamada a Jev. Ante fallo o baja confianza usa `fallback` (o `chat`)."""
    issue_list = sorted(issues)

    def classify(message: str, enabled: list[str]) -> tuple[str, str | None]:
        def fall_back():
            if fallback is None:
                return "chat", None
            result = fallback(message, enabled)
            return result if isinstance(result, tuple) else (result, None)

        criteria = {i: descriptions.get(i) or _DEFAULT_DESCRIPTIONS.get(i) or i for i in enabled}
        questions: dict = {
            "intent": {
                "type": "choice",
                "instructions": "¿Cuál es la intención del último mensaje del cliente?",
                "criteria": criteria,
            }
        }
        if issue_list:
            questions["issue"] = {
                "type": "choice",
                "instructions": "¿Sobre qué tema concreto consulta el cliente?",
                "criteria": {"none": "Ninguno de los siguientes", **{i: i.replace("_", " ") for i in issue_list}},
            }
        try:
            answers = jev.decide(message, questions)
            intent = answers["intent"]["choice"]
            if answers["intent"].get("confidence", 1.0) < min_confidence or intent not in enabled:
                return fall_back()
            issue = answers.get("issue", {}).get("choice")
            return intent, issue if issue in issue_list else None
        except Exception:
            log.exception("falló la clasificación con Jev; se usa el clasificador de respaldo")
            return fall_back()

    return classify
