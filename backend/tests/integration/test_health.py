from fastapi.testclient import TestClient

from atc.api.main import app


def test_health_is_served_under_api() -> None:
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}
