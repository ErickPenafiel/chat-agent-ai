import json
import logging
import re

from src.core.prompt_catalog import PromptStore
from src.llm.base import LLMProvider

log = logging.getLogger(__name__)


def make_llm_classifier(llm: LLMProvider, prompts: PromptStore):
    """Clasificador por LLM con el prompt versionado `intent_classifier`. Ante cualquier fallo -> chat."""

    def classify(message: str, enabled: list[str]) -> tuple[str, str | None]:
        system = prompts.get("intent_classifier")
        user = f"<customer_message>\n{message}\n</customer_message>"
        try:
            raw = llm.complete(system, user, json_mode=True)
            m = re.search(r"\{.*\}", raw, re.DOTALL)  # tolera ```json … ``` alrededor
            data = json.loads(m.group(0)) if m else {}
            intent = str(data.get("intent", "chat")).strip().lower()
            issue = data.get("issue")
            return (intent if intent in enabled else "chat", issue if isinstance(issue, str) else None)
        except Exception:
            log.exception("falló la clasificación por LLM; se usa chat")
            return "chat", None

    return classify
