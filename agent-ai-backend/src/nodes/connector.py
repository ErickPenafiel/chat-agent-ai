import logging

from src.connectors.base import ConnectorResult
from src.connectors.registry import ConnectorRegistry
from src.core.state import ConversationState

log = logging.getLogger(__name__)


def make_connector_node(registry: ConnectorRegistry):
    """Un solo nodo para todos los conectores: ejecuta los que coinciden con intención/issue."""

    def connector_node(state: ConversationState) -> dict:
        parts = list(state.get("response_parts", []))
        results = []
        for connector in registry.match(state["intent"], state.get("detected_issue")):
            try:
                result = connector.fetch(state)
            except Exception as e:  # un backend caído no debe tumbar la conversación
                log.exception("conector %s falló", connector.id)
                result = ConnectorResult(connector.id, found=False, error=str(e))
            results.append({
                "id": connector.id, "found": result.found, "data": result.data,
                "error": result.error, "prompt_key": connector.prompt_key,
            })
            # Si hubo error no se responde "no encontrado": el backend no dijo eso. Cae a RAG/handoff.
            if result.found or not result.error:
                text = connector.render(result)
                if text:
                    parts.append(text)
        return {"connector_results": results, "response_parts": parts}

    return connector_node
