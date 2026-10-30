from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from knowledge_core.config import DatabaseProvider, ProviderKind, ProviderRegistry


class SqlAlchemyDatabase:
    """Owns the process-wide engine and creates short-lived transactional sessions."""

    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session

    def dispose(self) -> None:
        self.engine.dispose()


def register_database_providers(registry: ProviderRegistry) -> None:
    registry.register(
        ProviderKind.DATABASE,
        DatabaseProvider.POSTGRES.value,
        lambda settings: SqlAlchemyDatabase(settings.database_url.get_secret_value()),
    )
