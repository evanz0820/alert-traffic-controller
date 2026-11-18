from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from atc.api.main import app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """App with a freshly seeded temp database (seeded by the lifespan on startup)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def run_id(client: TestClient) -> str:
    runs = client.get("/runs").json()
    default = [r for r in runs if r["label"] == "Default rules"]
    return str(default[-1]["id"])
