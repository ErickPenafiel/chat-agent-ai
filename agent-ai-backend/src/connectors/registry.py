"""Registro de conectores. Cada despliegue agrega sus implementaciones a AVAILABLE;
tenant.yaml (`connectors`) decide cuáles están activos. Cero activos = el agente responde solo con RAG."""

from collections.abc import Callable, Iterable

from src.connectors.base import Connector
from src.connectors.example import ExampleOrderStatus

AVAILABLE: dict[str, Callable[[], Connector]] = {
    ExampleOrderStatus.id: ExampleOrderStatus,
}


class ConnectorRegistry:
    def __init__(self, connectors: Iterable[Connector] = ()) -> None:
        self._by_id: dict[str, Connector] = {}
        for c in connectors:
            if c.id in self._by_id:
                raise ValueError(f"conector duplicado: {c.id!r}")
            self._by_id[c.id] = c

    def __iter__(self):
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, connector_id: str) -> Connector | None:
        return self._by_id.get(connector_id)

    def match(self, intent: str, issue: str | None) -> list[Connector]:
        return [c for c in self._by_id.values() if c.matches(intent, issue)]


def build_registry(active_ids: list[str]) -> ConnectorRegistry:
    unknown = [i for i in active_ids if i not in AVAILABLE]
    if unknown:
        raise ValueError(f"conectores desconocidos en tenant.yaml: {unknown}; disponibles: {sorted(AVAILABLE)}")
    return ConnectorRegistry(AVAILABLE[i]() for i in active_ids)
