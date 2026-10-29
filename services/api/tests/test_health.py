from api.main import app, get_harness_adapter
from fastapi.testclient import TestClient
from harness_core import FakeHarnessAdapter


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_exposes_harness_adapter_boundary() -> None:
    assert isinstance(get_harness_adapter(), FakeHarnessAdapter)
