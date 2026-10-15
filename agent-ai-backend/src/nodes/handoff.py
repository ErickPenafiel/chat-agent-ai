from src.core.state import ConversationState


def make_handoff_node():
    """Escalamiento a humano. Fase 1: solo marca el flag; TicketingSystem llega después."""

    def handoff_node(state: ConversationState) -> dict:
        return {"handoff": True, "response_parts": ["Lo derivo con una persona del equipo."]}

    return handoff_node
