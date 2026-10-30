from harness_core import FakeHarnessAdapter, HarnessAdapter
from knowledge_core import (
    MosaicSettings,
    ProviderKind,
    ProviderRegistry,
    get_settings,
    register_database_providers,
    register_storage_providers,
    register_task_queue_providers,
)


def main(
    adapter: HarnessAdapter | None = None,
    settings: MosaicSettings | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> int:
    settings = settings or get_settings()
    provider_registry = provider_registry or ProviderRegistry(settings)
    register_database_providers(provider_registry)
    register_storage_providers(provider_registry)
    register_task_queue_providers(provider_registry)
    task_queue = provider_registry.resolve(ProviderKind.QUEUE)
    object_storage = provider_registry.resolve(ProviderKind.STORAGE)
    adapter = adapter or FakeHarnessAdapter()
    _ = (adapter, task_queue, object_storage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
