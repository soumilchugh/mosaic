from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import UUID

from knowledge_core import (
    Asset,
    AssetKind,
    AssetService,
    CreateAsset,
    ObjectStorage,
    ProductEvent,
)
from knowledge_core.persistence import PlatformRepositories


def seed_task_workspace(
    repositories: PlatformRepositories,
    storage: ObjectStorage,
    asset_ids: list[UUID],
    workspace_root: Path,
) -> list[Path]:
    """Materialize selected durable assets under the agent's uploads directory."""

    service = AssetService(repositories, storage)
    assets = [repositories.assets.get(asset_id) for asset_id in asset_ids]
    return service.seed_workspace(assets, workspace_root)


def capture_generated_artifact(
    repositories: PlatformRepositories,
    storage: ObjectStorage,
    *,
    path: Path,
    knowledge_scope_id: UUID,
    project_id: UUID,
    agent_task_id: UUID,
    event_sequence: int,
    conversation_id: UUID | None = None,
    created_by_user_id: UUID | None = None,
    kind: AssetKind = AssetKind.GENERATED_REPORT,
) -> tuple[Asset, ProductEvent]:
    """Persist one sandbox artifact and emit its durable product event."""

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as source:
        return AssetService(repositories, storage).create_generated_artifact(
            CreateAsset(
                knowledge_scope_id=knowledge_scope_id,
                project_id=project_id,
                conversation_id=conversation_id,
                agent_task_id=agent_task_id,
                created_by_user_id=created_by_user_id,
                kind=kind,
                filename=path.name,
                mime_type=mime_type,
                source_metadata={"generated_path": str(path)},
            ),
            source,
            event_sequence=event_sequence,
        )
