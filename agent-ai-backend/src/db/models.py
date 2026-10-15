from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

STATUSES = ("draft", "published", "archived")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class KnowledgeBlock(Base):
    __tablename__ = "knowledge_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    # Intenciones que pueden usar el bloque (validadas contra tenant.yaml).
    intents: Mapped[list] = mapped_column(JSON, default=list)
    # Tema opcional (validado contra tenant.yaml `categories`).
    category: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    language: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True, default="published")
    version: Mapped[int] = mapped_column(default=1)
    # Ayudas de recuperación.
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    example_questions: Mapped[list] = mapped_column(JSON, default=list)
    # [{"id","type","url","alt"}]; los pasos referencian por id.
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    steps: Mapped[list] = mapped_column(JSON, default=list)  # [{"text","attachment_id"}]
    # Atributos propios del negocio, sin tocar el esquema.
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    # Reservado para búsqueda vectorial; hoy no se usa.
    embedding: Mapped[list | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class KnowledgeBlockVersion(Base):
    """Historial: una fila por guardado, con el estado completo resultante."""

    __tablename__ = "knowledge_block_versions"
    __table_args__ = (UniqueConstraint("block_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("knowledge_blocks.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    snapshot: Mapped[dict] = mapped_column(JSON)
    author: Mapped[str | None] = mapped_column(String(128), default=None)  # "api", "corrector", usuario…
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Prompt(Base):
    __tablename__ = "prompts"

    slug: Mapped[str] = mapped_column(String(128), primary_key=True)
    active_version: Mapped[int]


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("slug", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(ForeignKey("prompts.slug", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(128), default=None)  # "seed", "api", "corrector"…
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConversationOutcome(Base):
    """Una conversación (sesión) evaluada. La llenan las capas 0 (reglas+juez), 0.5 (simulación) y 1 (feedback)."""

    __tablename__ = "conversation_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(16), index=True, default="live")  # live | simulation | replay
    scenario: Mapped[str | None] = mapped_column(String(128), default=None)
    transcript: Mapped[list] = mapped_column(JSON, default=list)  # [{"role","content"}]
    turns: Mapped[int] = mapped_column(default=0)
    intent: Mapped[str | None] = mapped_column(String(64), default=None)
    handoff: Mapped[bool] = mapped_column(default=False)
    reply_modes: Mapped[list] = mapped_column(JSON, default=list)
    # Capa 0, reglas deterministas
    rule_flags: Mapped[list] = mapped_column(JSON, default=list)
    # Capa 0, juez LLM (nulos hasta que corre)
    judge_score: Mapped[float | None] = mapped_column(default=None)
    judge_resolved: Mapped[bool | None] = mapped_column(default=None)
    judge_issues: Mapped[list] = mapped_column(JSON, default=list)
    judged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Capa 1, feedback del cliente
    feedback_rating: Mapped[int | None] = mapped_column(default=None)
    feedback_comment: Mapped[str | None] = mapped_column(Text, default=None)
    # Capa 2: ya fue revisada por el corrector
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ImprovementProposal(Base):
    """Capa 2: cambio propuesto a KB o prompts. Nada se aplica sin aprobación humana."""

    __tablename__ = "improvement_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # kb_create | kb_update | prompt_update
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")  # pending|approved|rejected
    payload: Mapped[dict] = mapped_column(JSON)  # lo que se aplicaría
    before: Mapped[dict | None] = mapped_column(JSON, default=None)  # estado actual al proponer (para diff y conflictos)
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_outcome_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
