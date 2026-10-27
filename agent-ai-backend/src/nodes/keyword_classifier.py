import unicodedata

from src.core.config import TenantConfig
from src.nodes.intent import Classifier


def _norm(text: str) -> str:
    """Minúsculas y sin acentos, para comparar sin importar cómo escriba el cliente."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def make_keyword_classifier(config: TenantConfig) -> Classifier:
    """Clasificador local sin LLM: gana la intención con más palabras clave presentes; sin coincidencias -> chat."""
    keywords = {
        intent: [_norm(k) for k in cfg.keywords] for intent, cfg in config.intents.items() if cfg.keywords
    }

    def classify(message: str, enabled: list[str]) -> str:
        text = _norm(message)
        scores = {i: sum(k in text for k in kws) for i, kws in keywords.items() if i in enabled}
        if scores.get("escalate"):  # pedir una persona siempre gana
            return "escalate"
        best = max(scores, key=scores.get, default=None)
        return best if best and scores[best] > 0 else "chat"

    return classify
