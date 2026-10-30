from api.main import (
    app,
    create_app,
    get_application_settings,
    get_harness_adapter,
    get_provider_registry,
    get_task_queue,
)
from fastapi.testclient import TestClient
from harness_core import FakeHarnessAdapter
from knowledge_core import InMemoryTaskQueue, MosaicSettings, ProviderRegistry
from starlette.requests import Request


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_exposes_harness_adapter_boundary() -> None:
    assert isinstance(get_harness_adapter(), FakeHarnessAdapter)


def test_api_exposes_shared_settings_and_provider_registry() -> None:
    request = Request({"type": "http", "app": app})
    assert get_provider_registry(request).settings is get_application_settings(request)
    assert isinstance(get_task_queue(request), InMemoryTaskQueue)


def test_api_factory_accepts_injected_runtime_dependencies() -> None:
    settings = MosaicSettings(_env_file=None)
    registry = ProviderRegistry(settings)
    adapter = FakeHarnessAdapter()

    configured_app = create_app(settings, registry, adapter)

    assert configured_app.state.settings is settings
    assert configured_app.state.provider_registry is registry
    assert configured_app.state.harness_adapter is adapter
