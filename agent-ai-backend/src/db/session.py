import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import Base


def make_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("DATABASE_URL", "sqlite:///./agent.db")
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
    return engine


def make_session_factory(engine: Engine, create_tables: bool = False) -> sessionmaker[Session]:
    """En producción el esquema lo maneja Alembic; create_tables es solo para tests/dev en memoria."""
    if create_tables:
        Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
