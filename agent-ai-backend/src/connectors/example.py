"""Conector de ejemplo con datos SIMULADOS. Sirve para probar el patrón; no habla con ningún backend."""

import hashlib

from src.connectors.base import Connector, ConnectorResult
from src.core.state import ConversationState

_STATUSES = ("en preparación", "en camino", "entregado")


class ExampleOrderStatus(Connector):
    id = "example_order_status"
    intents = frozenset({"support"})
    issues = frozenset({"order_status"})
    prompt_key = "connector_example_order_status"
    response_template = "Su pedido {order_id} está {status}."
    not_found_message = "No encontré un pedido asociado a su cuenta."

    def fetch(self, state: ConversationState) -> ConnectorResult:
        entity = state.get("entity") or {}
        order_id = entity.get("id")
        if not order_id:
            return ConnectorResult(self.id, found=False)
        # Estado determinístico por id, para que los tests y demos sean repetibles.
        status = _STATUSES[int(hashlib.sha256(str(order_id).encode()).hexdigest(), 16) % len(_STATUSES)]
        return ConnectorResult(self.id, found=True, data={"order_id": order_id, "status": status})
