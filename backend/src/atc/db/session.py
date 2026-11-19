"""Database engines.

The app only ever reads: it opens the prebuilt snapshot (`backend/data/atc.db`) read-only
and immutable, so it runs on platforms with a read-only filesystem such as Vercel. The
snapshot is written once, at build time, by `atc.snapshot` through a writable engine.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, create_engine

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "atc.db"


def database_path() -> Path:
    return Path(os.environ.get("ATC_DATABASE_PATH", DEFAULT_DB_PATH))


def make_readonly_engine(path: Path | None = None) -> Engine:
    target = path or database_path()

    def connect() -> sqlite3.Connection:
        if not target.exists():
            raise FileNotFoundError(
                f"ATC snapshot not found at {target}. Build it with `make seed`."
            )
        # immutable=1: SQLite never writes (no journal, no locks), safe on read-only disks.
        return sqlite3.connect(
            f"file:{target}?mode=ro&immutable=1", uri=True, check_same_thread=False
        )

    # An explicit QueuePool: with a bare "sqlite://" URL SQLAlchemy would assume an
    # in-memory database and use a per-thread pool that closes connections still in use
    # by other request threads.
    return create_engine("sqlite://", creator=connect, poolclass=QueuePool, pool_size=8)


def make_writable_engine(path: Path) -> Engine:
    """Build-time only: used by atc.snapshot to create the snapshot file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


engine = make_readonly_engine()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
