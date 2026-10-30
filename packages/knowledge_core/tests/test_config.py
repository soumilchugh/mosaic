from __future__ import annotations

import pytest
from knowledge_core import (
    Environment,
    ModelProvider,
    MosaicSettings,
    ProviderAlreadyRegisteredError,
    ProviderKind,
    ProviderNotRegisteredError,
    ProviderRegistry,
    QueueProvider,
    SearchProvider,
    StorageProvider,
)
from pydantic import SecretStr, ValidationError


def test_settings_load_provider_selection_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOSAIC_ENVIRONMENT", "test")
    monkeypatch.setenv("MOSAIC_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MOSAIC_MODEL_NAME", "test-model")
    monkeypatch.setenv("MOSAIC_MODEL_API_KEY", "model-secret")
    monkeypatch.setenv("MOSAIC_SEARCH_PROVIDER", "tavily")
    monkeypatch.setenv("MOSAIC_SEARCH_API_KEY", "search-secret")
    monkeypatch.setenv("MOSAIC_QUEUE_PROVIDER", "postgres")

    settings = MosaicSettings(_env_file=None)

    assert settings.environment is Environment.TEST
    assert settings.model_provider is ModelProvider.OPENAI
    assert settings.model_name == "test-model"
    assert settings.search_provider is SearchProvider.TAVILY
    assert settings.queue_provider is QueueProvider.POSTGRES
    assert settings.provider_name(ProviderKind.MODEL) == "openai"


def test_settings_do_not_expose_secrets() -> None:
    settings = MosaicSettings(
        _env_file=None,
        database_url=SecretStr("postgresql://user:database-secret@example.test/mosaic"),
        model_provider=ModelProvider.OPENAI,
        model_api_key=SecretStr("model-secret"),
    )

    rendered = f"{settings!r}\n{settings.model_dump_json()}\n{settings.safe_summary()}"

    assert "database-secret" not in rendered
    assert "model-secret" not in rendered
    assert settings.safe_summary() == {
        "environment": "development",
        "database_provider": "postgres",
        "model_provider": "openai",
        "search_provider": "none",
        "storage_provider": "filesystem",
        "queue_provider": "memory",
        "sandbox_provider": "local",
        "model_name": "fake",
        "storage_bucket": "mosaic",
    }


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"model_provider": "anthropic"}, "MODEL_API_KEY"),
        ({"search_provider": "perplexity"}, "SEARCH_API_KEY"),
        ({"storage_provider": "minio"}, "STORAGE_ENDPOINT"),
    ],
)
def test_settings_reject_incomplete_provider_configuration(
    values: dict[str, str], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        MosaicSettings(_env_file=None, **values)


def test_registry_lazily_resolves_and_caches_the_configured_provider() -> None:
    settings = MosaicSettings(_env_file=None)
    registry = ProviderRegistry(settings)
    constructed: list[str] = []

    def build_model(config: MosaicSettings) -> object:
        constructed.append(config.model_name)
        return object()

    registry.register(ProviderKind.MODEL, "fake", build_model)

    first = registry.resolve(ProviderKind.MODEL)
    second = registry.resolve(ProviderKind.MODEL)

    assert first is second
    assert constructed == ["fake"]
    assert registry.registered_names(ProviderKind.MODEL) == ("fake",)


def test_registry_rejects_duplicates_and_reports_missing_selection() -> None:
    settings = MosaicSettings(_env_file=None, storage_provider=StorageProvider.FILESYSTEM)
    registry = ProviderRegistry(settings)
    registry.register(ProviderKind.STORAGE, "filesystem", lambda _: "first")

    with pytest.raises(ProviderAlreadyRegisteredError, match="storage:filesystem"):
        registry.register(ProviderKind.STORAGE, "filesystem", lambda _: "second")

    with pytest.raises(ProviderNotRegisteredError, match="queue:memory"):
        registry.resolve(ProviderKind.QUEUE)

    registry.register(
        ProviderKind.STORAGE,
        "filesystem",
        lambda _: "replacement",
        replace=True,
    )
    assert registry.resolve(ProviderKind.STORAGE) == "replacement"
