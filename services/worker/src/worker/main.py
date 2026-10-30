from harness_core import FakeHarnessAdapter, HarnessAdapter
from knowledge_core import MosaicSettings, ProviderRegistry, get_settings


def main(
    adapter: HarnessAdapter | None = None,
    settings: MosaicSettings | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> int:
    settings = settings or get_settings()
    provider_registry = provider_registry or ProviderRegistry(settings)
    adapter = adapter or FakeHarnessAdapter()
    _ = (adapter, provider_registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
