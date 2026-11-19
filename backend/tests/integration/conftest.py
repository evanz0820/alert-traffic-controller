from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atc.api.main import app
from atc.db.session import database_path
from atc.snapshot import DEFAULT_RUN_ID, build_snapshot


@pytest.fixture(scope="session")
def snapshot_path() -> Path:
    """One snapshot, built once per test session at the path the app reads."""
    path = database_path()
    build_snapshot(path)
    return path


@pytest.fixture(scope="session")
def client(snapshot_path: Path) -> Iterator[TestClient]:
    """The read-only app serving the session snapshot."""
    with TestClient(app, base_url="http://testserver/api") as test_client:
        yield test_client


@pytest.fixture(scope="session")
def run_id(client: TestClient) -> str:
    return DEFAULT_RUN_ID
