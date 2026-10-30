from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ProviderKind(StrEnum):
    DATABASE = "database"
    MODEL = "model"
    SEARCH = "search"
    STORAGE = "storage"
    QUEUE = "queue"
    SANDBOX = "sandbox"


class DatabaseProvider(StrEnum):
    POSTGRES = "postgres"


class ModelProvider(StrEnum):
    FAKE = "fake"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class SearchProvider(StrEnum):
    NONE = "none"
    TAVILY = "tavily"
    PERPLEXITY = "perplexity"


class StorageProvider(StrEnum):
    FILESYSTEM = "filesystem"
    MINIO = "minio"
    SUPABASE = "supabase"
    S3 = "s3"


class QueueProvider(StrEnum):
    MEMORY = "memory"
    POSTGRES = "postgres"
    SQS = "sqs"


class SandboxProvider(StrEnum):
    LOCAL = "local"
    DOCKER = "docker"


class MosaicSettings(BaseSettings):
    """Typed application settings shared by API and worker processes."""

    model_config = SettingsConfigDict(
        env_prefix="MOSAIC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    environment: Environment = Environment.DEVELOPMENT
    database_provider: DatabaseProvider = DatabaseProvider.POSTGRES
    database_url: SecretStr = SecretStr("postgresql+psycopg://mosaic:mosaic@localhost:5432/mosaic")

    model_provider: ModelProvider = ModelProvider.FAKE
    model_name: str = "fake"
    model_api_key: SecretStr | None = None

    search_provider: SearchProvider = SearchProvider.NONE
    search_api_key: SecretStr | None = None

    storage_provider: StorageProvider = StorageProvider.FILESYSTEM
    storage_root: Path = Path(".mosaic/objects")
    storage_endpoint: str | None = None
    storage_bucket: str = "mosaic"
    storage_access_key: SecretStr | None = None
    storage_secret_key: SecretStr | None = None

    queue_provider: QueueProvider = QueueProvider.MEMORY
    sandbox_provider: SandboxProvider = SandboxProvider.LOCAL

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> MosaicSettings:
        if self.model_provider is not ModelProvider.FAKE and self.model_api_key is None:
            raise ValueError(f"{self.model_provider.value} model provider requires MODEL_API_KEY")
        if self.search_provider is not SearchProvider.NONE and self.search_api_key is None:
            raise ValueError(
                f"{self.search_provider.value} search provider requires SEARCH_API_KEY"
            )
        if self.storage_provider is StorageProvider.MINIO:
            if self.storage_endpoint is None:
                raise ValueError("minio storage provider requires STORAGE_ENDPOINT")
            if self.storage_access_key is None or self.storage_secret_key is None:
                raise ValueError("minio storage provider requires storage credentials")
        return self

    def provider_name(self, kind: ProviderKind) -> str:
        providers = {
            ProviderKind.DATABASE: self.database_provider,
            ProviderKind.MODEL: self.model_provider,
            ProviderKind.SEARCH: self.search_provider,
            ProviderKind.STORAGE: self.storage_provider,
            ProviderKind.QUEUE: self.queue_provider,
            ProviderKind.SANDBOX: self.sandbox_provider,
        }
        return providers[kind].value

    def safe_summary(self) -> dict[str, str]:
        """Return log-safe, non-secret configuration metadata."""

        return {
            "environment": self.environment.value,
            **{f"{kind.value}_provider": self.provider_name(kind) for kind in ProviderKind},
            "model_name": self.model_name,
            "storage_bucket": self.storage_bucket,
        }


@lru_cache(maxsize=1)
def get_settings() -> MosaicSettings:
    return MosaicSettings()


class ProviderRegistryError(RuntimeError):
    pass


class ProviderAlreadyRegisteredError(ProviderRegistryError):
    pass


class ProviderNotRegisteredError(ProviderRegistryError):
    pass


ProviderFactory = Callable[[MosaicSettings], Any]


class ProviderRegistry:
    """Resolves configured provider implementations without importing vendor SDKs."""

    def __init__(self, settings: MosaicSettings) -> None:
        self.settings = settings
        self._factories: dict[tuple[ProviderKind, str], ProviderFactory] = {}
        self._instances: dict[tuple[ProviderKind, str], Any] = {}

    def register(
        self,
        kind: ProviderKind,
        name: str,
        factory: ProviderFactory,
        *,
        replace: bool = False,
    ) -> None:
        key = (kind, name.lower())
        if key in self._factories and not replace:
            raise ProviderAlreadyRegisteredError(
                f"provider {kind.value}:{name.lower()} is already registered"
            )
        self._factories[key] = factory
        self._instances.pop(key, None)

    def resolve(self, kind: ProviderKind) -> Any:
        name = self.settings.provider_name(kind)
        key = (kind, name)
        if key not in self._factories:
            raise ProviderNotRegisteredError(f"provider {kind.value}:{name} is not registered")
        if key not in self._instances:
            self._instances[key] = self._factories[key](self.settings)
        return self._instances[key]

    def registered_names(self, kind: ProviderKind) -> tuple[str, ...]:
        return tuple(
            sorted(name for registered_kind, name in self._factories if registered_kind == kind)
        )
