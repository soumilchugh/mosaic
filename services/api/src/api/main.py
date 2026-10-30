from fastapi import FastAPI, Request
from harness_core import FakeHarnessAdapter, HarnessAdapter
from knowledge_core import (
    MosaicSettings,
    ProviderKind,
    ProviderRegistry,
    TaskQueue,
    get_settings,
    register_task_queue_providers,
)


def create_app(
    settings: MosaicSettings | None = None,
    provider_registry: ProviderRegistry | None = None,
    harness_adapter: HarnessAdapter | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Mosaic API")
    app.state.settings = settings
    app.state.provider_registry = provider_registry or ProviderRegistry(settings)
    register_task_queue_providers(app.state.provider_registry)
    app.state.harness_adapter = harness_adapter or FakeHarnessAdapter()
    return app


app = create_app()


def get_application_settings(request: Request) -> MosaicSettings:
    return request.app.state.settings


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry


def get_task_queue(request: Request) -> TaskQueue:
    return get_provider_registry(request).resolve(ProviderKind.QUEUE)


def get_harness_adapter() -> HarnessAdapter:
    return app.state.harness_adapter


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
