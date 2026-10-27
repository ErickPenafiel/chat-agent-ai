"""Grafo de orquestación genérico. No conoce ningún negocio: todo sale de TenantConfig."""

from langgraph.graph import END, START, StateGraph

from src.connectors.registry import ConnectorRegistry, build_registry
from src.core.config import TenantConfig
from src.core.intents import RETRIEVAL_INTENTS
from src.core.prompt_catalog import PromptStore
from src.core.state import ConversationState
from src.llm.base import LLMProvider
from src.llm.jev import JevClient
from src.nodes.capture import make_capture_node
from src.nodes.connector import make_connector_node
from src.nodes.handoff import make_handoff_node
from src.nodes.identity import EntityResolver, make_identity_node, no_resolver
from src.nodes.intent import Classifier, default_classifier, make_intent_node
from src.nodes.jev_classifier import make_jev_classifier
from src.nodes.keyword_classifier import make_keyword_classifier
from src.nodes.llm_classifier import make_llm_classifier
from src.nodes.media import make_media_node
from src.nodes.response import make_response_node
from src.nodes.retrieval import Retriever, empty_retriever, make_retrieval_node
from src.nodes.verify import make_verify_node


def _capture_pending(config: TenantConfig, state: ConversationState) -> bool:
    """Hay captura en curso, o la intención tiene campos sin completar."""
    if state.get("awaiting_capture_field"):
        return True
    fields = config.intents[state["intent"]].capture_fields
    return any(f not in state.get("capture", {}) for f in fields)


def build_graph(
    config: TenantConfig,
    classifier: Classifier = default_classifier,
    retriever: Retriever = empty_retriever,
    checkpointer=None,
    connectors: ConnectorRegistry | None = None,
    entity_resolver: EntityResolver = no_resolver,
    llm: LLMProvider | None = None,
    prompts: PromptStore | None = None,
    jev: JevClient | None = None,
):
    registry = connectors if connectors is not None else build_registry(config.connectors)
    if llm is not None and prompts is None:
        raise ValueError("llm requiere prompts (PromptStore)")
    valid_issues = frozenset(i for c in registry for i in c.issues)
    if llm is not None and classifier is default_classifier:
        classifier = make_llm_classifier(llm, prompts)
    elif classifier is default_classifier and any(c.keywords for c in config.intents.values()):
        classifier = make_keyword_classifier(config)
    if jev is not None and config.jev is not None:
        classifier = make_jev_classifier(
            jev,
            {k: v.description for k, v in config.intents.items() if v.description},
            valid_issues,
            config.jev.min_confidence,
            fallback=None if classifier is default_classifier else classifier,
        )

    g = StateGraph(ConversationState)

    g.add_node("media", make_media_node())
    g.add_node("identity", make_identity_node(config, entity_resolver))
    g.add_node("intent", make_intent_node(config, classifier, valid_issues))
    g.add_node("capture", make_capture_node(config))
    g.add_node("connector", make_connector_node(registry))
    g.add_node("retrieval", make_retrieval_node(retriever))
    g.add_node("response", make_response_node(config, registry, llm, prompts))
    g.add_node("handoff", make_handoff_node())

    g.add_edge(START, "media" if config.media_enabled else "identity")
    if config.media_enabled:
        g.add_edge("media", "identity")
    g.add_edge("identity", "intent")

    def route(state: ConversationState) -> str:
        intent = state["intent"]
        if intent == "escalate":
            return "handoff"
        if state.get("awaiting_capture_field"):  # la respuesta del cliente es el dato pedido
            return "capture"
        capture_first = (
            config.intents[intent].capture_before_answer and _capture_pending(config, state)
        )
        if capture_first:
            return "capture"
        if registry.match(intent, state.get("detected_issue")):
            return "connector"
        if intent in RETRIEVAL_INTENTS:
            return "retrieval"
        # intenciones custom o chat: si tienen campos que capturar van a captura
        return "capture" if _capture_pending(config, state) else "response"

    g.add_conditional_edges(
        "intent",
        route,
        {"handoff": "handoff", "capture": "capture", "connector": "connector",
         "retrieval": "retrieval", "response": "response"},
    )

    # Con captura-después: retrieval -> (capture si falta algo) -> response.
    def after_retrieval(state: ConversationState) -> str:
        return "capture" if _capture_pending(config, state) else "response"

    g.add_conditional_edges(
        "retrieval", after_retrieval, {"capture": "capture", "response": "response"}
    )
    # Si el conector trajo el dato, no se mezcla con la KB; si no, se cae a RAG.
    def after_connector(state: ConversationState) -> str:
        if any(r["found"] for r in state.get("connector_results", [])):
            return after_retrieval(state)
        return "retrieval" if state["intent"] in RETRIEVAL_INTENTS else after_retrieval(state)

    g.add_conditional_edges(
        "connector", after_connector,
        {"retrieval": "retrieval", "capture": "capture", "response": "response"},
    )
    # Tras completar la captura "antepuesta", se responde la consulta que había quedado pendiente.
    def after_capture(state: ConversationState) -> str:
        if not state.get("answer_pending"):
            return "response"
        if registry.match(state["intent"], state.get("detected_issue")):
            return "connector"
        return "retrieval" if state["intent"] in RETRIEVAL_INTENTS else "response"

    g.add_conditional_edges(
        "capture", after_capture, {"connector": "connector", "retrieval": "retrieval", "response": "response"}
    )
    g.add_edge("handoff", "response")
    if config.verify_responses and llm is not None:
        g.add_node("verify", make_verify_node(llm, prompts))
        g.add_edge("response", "verify")
        g.add_edge("verify", END)
    else:
        g.add_edge("response", END)

    return g.compile(checkpointer=checkpointer)
