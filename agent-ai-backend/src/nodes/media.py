from src.core.state import ConversationState


def make_media_node():
    """Placeholder: transcribe/describe adjuntos. Sin proveedor en esta fase."""

    def media_node(state: ConversationState) -> dict:
        return {"transcript": None}

    return media_node
