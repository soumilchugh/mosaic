from __future__ import annotations

import hashlib
import os
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol
from urllib.parse import quote, unquote, urlsplit
from uuid import UUID, uuid4

from knowledge_core.config import ProviderKind, ProviderRegistry, StorageProvider
from knowledge_core.contracts import Asset, AssetKind, ProductEvent
from knowledge_core.persistence import PlatformRepositories

_COPY_BUFFER_SIZE = 1024 * 1024
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")
_SAFE_BUCKET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")


class ObjectStorageError(RuntimeError):
    pass


class InvalidObjectKeyError(ObjectStorageError):
    pass


class ObjectNotFoundError(ObjectStorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    uri: str
    size_bytes: int
    checksum_sha256: str


class ObjectStorage(Protocol):
    def put(self, key: str, source: BinaryIO) -> StoredObject: ...

    @contextmanager
    def open(self, uri: str) -> Iterator[BinaryIO]: ...

    def delete(self, uri: str) -> None: ...


def safe_filename(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    name = _SAFE_FILENAME.sub("_", name)
    if name in {"", ".", ".."}:
        raise ValueError("filename must identify a file")
    return name[:255]


class FilesystemObjectStorage:
    """Local object-store adapter with bucket URIs and atomic writes."""

    def __init__(self, root: Path, bucket: str) -> None:
        if not _SAFE_BUCKET.fullmatch(bucket):
            raise ValueError(
                "bucket must contain only letters, numbers, dots, dashes, or underscores"
            )
        self.root = root.expanduser().resolve()
        self.bucket = bucket
        self.bucket_root = self.root / bucket
        self.bucket_root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, source: BinaryIO) -> StoredObject:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("wb") as destination:
                while chunk := source.read(_COPY_BUFFER_SIZE):
                    digest.update(chunk)
                    size += len(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredObject(self._uri(key), size, digest.hexdigest())

    @contextmanager
    def open(self, uri: str) -> Iterator[BinaryIO]:
        path = self._path_for_uri(uri)
        try:
            with path.open("rb") as source:
                yield source
        except FileNotFoundError as exc:
            raise ObjectNotFoundError(uri) from exc

    def delete(self, uri: str) -> None:
        self._path_for_uri(uri).unlink(missing_ok=True)

    def _path_for_uri(self, uri: str) -> Path:
        parsed = urlsplit(uri)
        if (
            parsed.scheme != "object"
            or parsed.netloc != self.bucket
            or parsed.query
            or parsed.fragment
        ):
            raise InvalidObjectKeyError("object URI does not belong to this storage bucket")
        return self._path_for_key(unquote(parsed.path.lstrip("/")))

    def _path_for_key(self, key: str) -> Path:
        pure_key = PurePosixPath(key)
        if pure_key.is_absolute() or any(part in {"", ".", ".."} for part in pure_key.parts):
            raise InvalidObjectKeyError(f"invalid object key: {key}")
        path = (self.bucket_root / Path(*pure_key.parts)).resolve()
        if not path.is_relative_to(self.bucket_root):
            raise InvalidObjectKeyError(f"object key escapes bucket: {key}")
        return path

    def _uri(self, key: str) -> str:
        return f"object://{self.bucket}/{quote(key, safe='/')}"


@dataclass(frozen=True)
class CreateAsset:
    knowledge_scope_id: UUID
    project_id: UUID
    created_by_user_id: UUID | None
    kind: AssetKind
    filename: str
    mime_type: str
    conversation_id: UUID | None = None
    agent_task_id: UUID | None = None
    source_url: str | None = None
    source_metadata: dict[str, object] | None = None


class AssetService:
    """Coordinates object bytes, scoped metadata, and artifact events."""

    def __init__(self, repositories: PlatformRepositories, storage: ObjectStorage) -> None:
        self.repositories = repositories
        self.storage = storage

    def create(self, command: CreateAsset, source: BinaryIO) -> Asset:
        asset_id = uuid4()
        filename = safe_filename(command.filename)
        key = f"{command.knowledge_scope_id}/{asset_id}/{filename}"
        stored = self.storage.put(key, source)
        asset = Asset(
            id=asset_id,
            knowledge_scope_id=command.knowledge_scope_id,
            project_id=command.project_id,
            conversation_id=command.conversation_id,
            agent_task_id=command.agent_task_id,
            created_by_user_id=command.created_by_user_id,
            kind=command.kind,
            filename=filename,
            mime_type=command.mime_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            storage_uri=stored.uri,
            source_url=command.source_url,
            source_metadata=command.source_metadata or {},
        )
        try:
            return self.repositories.assets.add(asset)
        except Exception:
            self.storage.delete(stored.uri)
            raise

    def get(self, asset_id: UUID) -> Asset:
        return self.repositories.assets.get(asset_id)

    @contextmanager
    def open(self, asset_id: UUID) -> Iterator[tuple[Asset, BinaryIO]]:
        asset = self.get(asset_id)
        with self.storage.open(asset.storage_uri) as source:
            yield asset, source

    def create_generated_artifact(
        self,
        command: CreateAsset,
        source: BinaryIO,
        *,
        event_sequence: int,
    ) -> tuple[Asset, ProductEvent]:
        if command.agent_task_id is None:
            raise ValueError("generated artifacts require an agent task")
        asset = self.create(command, source)
        try:
            event = self.repositories.events.add(
                ProductEvent(
                    project_id=command.project_id,
                    conversation_id=command.conversation_id,
                    agent_task_id=command.agent_task_id,
                    sequence=event_sequence,
                    type="artifact.generated",
                    payload={
                        "asset_id": str(asset.id),
                        "filename": asset.filename,
                        "mime_type": asset.mime_type,
                        "size_bytes": asset.size_bytes,
                    },
                )
            )
        except Exception:
            self.storage.delete(asset.storage_uri)
            raise
        return asset, event

    def seed_workspace(self, assets: list[Asset], workspace_root: Path) -> list[Path]:
        upload_root = workspace_root / "uploads"
        upload_root.mkdir(parents=True, exist_ok=True)
        seeded: list[Path] = []
        for asset in assets:
            destination = upload_root / f"{asset.id}_{safe_filename(asset.filename)}"
            with self.storage.open(asset.storage_uri) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=_COPY_BUFFER_SIZE)
            seeded.append(destination)
        return seeded


def register_storage_providers(registry: ProviderRegistry) -> None:
    registry.register(
        ProviderKind.STORAGE,
        StorageProvider.FILESYSTEM.value,
        lambda settings: FilesystemObjectStorage(settings.storage_root, settings.storage_bucket),
    )
