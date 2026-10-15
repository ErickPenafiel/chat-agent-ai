"""Contrato de conector: un backend de datos en vivo detrás de una interfaz.

El grafo no tiene nodos por integración; itera el registro (ver registry.py).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.core.state import ConversationState


@dataclass
class ConnectorResult:
    connector_id: str
    found: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Connector(ABC):
    id: str
    # Qué lo dispara. Con `issues` definidos exige detected_issue en esa lista (y la intención, si hay);
    # sin `issues`, basta con que coincida la intención.
    intents: frozenset[str] = frozenset()
    issues: frozenset[str] = frozenset()
    # Clave del prompt versionado con el que se responde con este dato (Fase 5).
    prompt_key: str
    # Respuesta por defecto sin LLM: se rellena con str.format_map(data).
    response_template: str = ""
    not_found_message: str = ""

    def matches(self, intent: str, issue: str | None) -> bool:
        if self.issues:
            return issue in self.issues and (not self.intents or intent in self.intents)
        return intent in self.intents

    @abstractmethod
    def fetch(self, state: ConversationState) -> ConnectorResult:
        """Consulta el backend. Puede lanzar excepciones: el nodo las captura y las marca como error."""

    def render(self, result: ConnectorResult) -> str:
        if not result.found:
            return self.not_found_message
        return self.response_template.format_map(result.data)
