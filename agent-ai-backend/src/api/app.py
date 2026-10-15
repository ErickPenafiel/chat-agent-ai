import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langgraph.checkpoint.memory import MemorySaver

from src.api import auth as auth_api
from src.api import channels as channels_api
from src.api import connectors as connectors_api
from src.api import evaluation as evaluation_api
from src.api import knowledge_blocks
from src.api import prompts as prompts_api
from src.channels.base import MessagingChannel
from src.channels.registry import build_channels
from src.connectors.registry import build_registry
from src.core.dispatcher import Deduper
from src.auth.firebase import FirebaseVerifier
from src.eval.recorder import OutcomeRecorder
from src.core.prompt_catalog import PromptStore, default_prompts, prompt_variables
from src.llm.base import LLMProvider
from src.llm.factory import build_llm
from src.llm.health import verify_llm
from src.core.graph import build_graph
from src.nodes.kb_retriever import make_kb_retriever
from src.core.config import TenantConfig, load_tenant_config
from src.db.knowledge import KBRules, find_orphans
from src.db.session import make_engine, make_session_factory

log = logging.getLogger(__name__)


def create_app(
    config: TenantConfig | None = None,
    database_url: str | None = None,
    create_tables: bool | None = None,
    channels: dict[str, MessagingChannel] | None = None,
    llm: LLMProvider | None = None,
    entity_resolver=None,
    auth_verifier=None,
) -> FastAPI:
    """El esquema lo crea Alembic (`alembic upgrade head`); create_tables es para tests/dev en memoria."""
    config = config or load_tenant_config(os.environ.get("TENANT_CONFIG", "config/tenant.yaml"))
    app = FastAPI(title=f"Agente — {config.business_name}")
    app.state.config = config
    if config.auth.mode == "firebase":
        app.state.auth_verifier = auth_verifier or FirebaseVerifier(config.auth.firebase_project_id)
    elif os.environ.get("ALLOW_INSECURE_AUTH", "").lower() in ("1", "true"):
        log.warning("auth.mode=disabled (ALLOW_INSECURE_AUTH): la API de administración está ABIERTA. Solo desarrollo.")
    else:
        # Falla cerrado: abrir la API de administración exige una decisión explícita en el entorno.
        raise RuntimeError(
            "auth.mode=disabled deja la API de administración abierta. Para desarrollo local define "
            "ALLOW_INSECURE_AUTH=1; en producción usa auth.mode=firebase."
        )
    if config.cors.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors.allowed_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,  # el token va en la cabecera, no en cookies
        )
    if create_tables is None:
        create_tables = bool(database_url and ":memory:" in database_url)
    app.state.session_factory = make_session_factory(make_engine(database_url), create_tables)

    with app.state.session_factory() as db:
        for block, problems in find_orphans(db, KBRules.from_config(config)):
            log.warning("bloque KB %s huérfano respecto a tenant.yaml: %s", block.id, problems)

    app.state.channels = channels if channels is not None else build_channels(config.channels)
    app.state.deduper = Deduper()
    app.state.recorder = OutcomeRecorder(app.state.session_factory, config.thresholds.session_timeout_minutes)
    app.state.connectors = build_registry(config.connectors)
    app.state.llm = llm if llm is not None else build_llm(config.llm)
    if llm is None:  # solo un LLM construido desde la config toca la red; los inyectados (tests) no
        verify_llm(app.state.llm)
    app.state.prompts = PromptStore(
        app.state.session_factory,
        default_prompts(config, app.state.connectors),
        prompt_variables(config, app.state.connectors),
    )
    app.state.prompts.seed()
    # MemorySaver es solo para dev; en producción va AsyncPostgresSaver (plan: checkpointing en Postgres).
    app.state.graph = build_graph(
        config,
        retriever=make_kb_retriever(app.state.session_factory, language=config.tone.language),
        checkpointer=MemorySaver(),
        connectors=app.state.connectors,
        llm=app.state.llm,
        prompts=app.state.prompts,
        **({"entity_resolver": entity_resolver} if entity_resolver else {}),
    )

    admin = [Depends(auth_api.require_admin)]
    app.include_router(auth_api.router)  # /health abierto; /auth/me exige token
    app.include_router(knowledge_blocks.router, dependencies=admin)
    app.include_router(prompts_api.router, dependencies=admin)
    app.include_router(connectors_api.router, dependencies=admin)
    app.include_router(evaluation_api.outcomes_router, dependencies=admin)
    app.include_router(evaluation_api.proposals_router, dependencies=admin)
    # Webhooks de canales: públicos (los reales se protegen con la firma del proveedor). El canal mock exige token.
    app.include_router(channels_api.router)
    return app
