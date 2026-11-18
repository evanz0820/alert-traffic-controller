"""Database engine and session factory (single-file SQLite)."""

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "atc.db"


def database_url() -> str:
    return os.environ.get("ATC_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url(), connect_args={"check_same_thread": False})


engine = make_engine()


def init_db(db_engine: Engine | None = None) -> None:
    SQLModel.metadata.create_all(db_engine or engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
