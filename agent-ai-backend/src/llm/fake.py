"""Proveedor falso para tests y demos sin red."""

from collections.abc import Callable

from src.llm.base import LLMProvider


class FakeLLM(LLMProvider):
    def __init__(self, handler: Callable[[str, str, bool], str]) -> None:
        self.handler = handler
        self.calls: list[tuple[str, str, bool]] = []

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        self.calls.append((system, user, json_mode))
        return self.handler(system, user, json_mode)
