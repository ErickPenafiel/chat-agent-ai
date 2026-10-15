from collections.abc import Callable
from typing import Any

from src.core.config import TenantConfig
from src.core.state import ConversationState

# Resolver inyectable: estado -> entidad del negocio {"id": ..., ...} o None.
# El tipo de entidad (pedido, cuenta, turno…) lo define tenant.yaml `identity_entity_type`.
EntityResolver = Callable[[ConversationState], dict[str, Any] | None]


def no_resolver(state: ConversationState) -> dict[str, Any] | None:
    return None


def make_identity_node(config: TenantConfig, resolver: EntityResolver = no_resolver):
    """¿A qué entidad del negocio corresponde el mensaje? Sin resolver registrado devuelve None."""

    def identity_node(state: ConversationState) -> dict:
        return {"entity": resolver(state)}

    return identity_node
