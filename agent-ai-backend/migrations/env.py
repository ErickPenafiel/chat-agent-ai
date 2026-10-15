import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


from src.db.models import Base

target_metadata = Base.metadata


def _url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///./agent.db")


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
