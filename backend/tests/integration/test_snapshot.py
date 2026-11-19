"""The committed snapshot must match what the current code produces."""

from pathlib import Path

import pytest
from sqlmodel import Session, select

from atc.analytics.summary import compute_summary
from atc.db.models import SimRun
from atc.db.session import DEFAULT_DB_PATH, make_readonly_engine
from atc.snapshot import DEFAULT_RUN_ID


def _summary(path: Path) -> dict[str, object]:
    engine = make_readonly_engine(path)
    with Session(engine) as session:
        run = session.exec(select(SimRun).where(SimRun.id == DEFAULT_RUN_ID)).one()
        return compute_summary(session, run).model_dump(mode="json")


@pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="snapshot not built")
def test_committed_snapshot_is_current(snapshot_path: Path) -> None:
    assert _summary(DEFAULT_DB_PATH) == _summary(snapshot_path), (
        "backend/data/atc.db is stale; rebuild it with `make seed` and commit it"
    )


def test_readonly_engine_refuses_writes(snapshot_path: Path) -> None:
    engine = make_readonly_engine(snapshot_path)
    with engine.connect() as conn, pytest.raises(Exception, match=r"readonly|read-only"):
        conn.exec_driver_sql("CREATE TABLE nope (id INTEGER)")


def test_missing_snapshot_explains_how_to_build_it(tmp_path: Path) -> None:
    engine = make_readonly_engine(tmp_path / "missing.db")
    with pytest.raises(FileNotFoundError, match="make seed"):
        engine.connect()


def test_readonly_engine_serves_concurrent_threads(snapshot_path: Path) -> None:
    """FastAPI runs sync endpoints on a thread pool; connections must not be shared."""
    from concurrent.futures import ThreadPoolExecutor

    from atc.analytics.rows import load_run_rows

    engine = make_readonly_engine(snapshot_path)

    def count_rows(_: int) -> int:
        with Session(engine) as session:
            return len(load_run_rows(session, DEFAULT_RUN_ID).rows)

    with ThreadPoolExecutor(max_workers=12) as pool:
        counts = list(pool.map(count_rows, range(24)))
    assert len(set(counts)) == 1 and counts[0] > 0
