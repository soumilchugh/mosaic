from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from knowledge_core import (
    Asset,
    AssetKind,
    AssetService,
    CreateAsset,
    ObjectNotFoundError,
    ObjectStorage,
    ProviderKind,
    SqlAlchemyDatabase,
)
from knowledge_core.persistence import (
    EntityNotFoundError,
    ProjectAccessDeniedError,
    ProjectBoundaryError,
    ProjectContext,
    SqlAlchemyRepositories,
)

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


def get_asset_service(
    request: Request,
    project_id: UUID,
    x_user_id: Annotated[UUID, Header()],
) -> Iterator[AssetService]:
    registry = request.app.state.provider_registry
    database: SqlAlchemyDatabase = registry.resolve(ProviderKind.DATABASE)
    storage: ObjectStorage = registry.resolve(ProviderKind.STORAGE)
    with database.session() as session:
        try:
            repositories = SqlAlchemyRepositories(session, ProjectContext(project_id, x_user_id))
        except ProjectAccessDeniedError as exc:
            raise HTTPException(status_code=403, detail="project access denied") from exc
        yield AssetService(repositories, storage)


AssetServiceDependency = Annotated[AssetService, Depends(get_asset_service)]


@router.post("", response_model=Asset, status_code=201)
def upload_asset(
    project_id: UUID,
    knowledge_scope_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    service: AssetServiceDependency,
    x_user_id: Annotated[UUID, Header()],
    kind: Annotated[AssetKind, Form()] = AssetKind.UPLOAD,
    conversation_id: Annotated[UUID | None, Form()] = None,
    agent_task_id: Annotated[UUID | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
    source_metadata: Annotated[str | None, Form()] = None,
) -> Asset:
    metadata = _parse_metadata(source_metadata)
    try:
        return service.create(
            CreateAsset(
                knowledge_scope_id=knowledge_scope_id,
                project_id=project_id,
                created_by_user_id=x_user_id,
                kind=kind,
                filename=file.filename or "upload",
                mime_type=file.content_type or "application/octet-stream",
                conversation_id=conversation_id,
                agent_task_id=agent_task_id,
                source_url=source_url,
                source_metadata=metadata,
            ),
            file.file,
        )
    except ProjectBoundaryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: UUID, service: AssetServiceDependency) -> Asset:
    try:
        return service.get(asset_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc


@router.get("/{asset_id}/content")
def get_asset_content(asset_id: UUID, service: AssetServiceDependency) -> StreamingResponse:
    try:
        asset = service.get(asset_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc

    def stream() -> Iterator[bytes]:
        try:
            with service.storage.open(asset.storage_uri) as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk
        except ObjectNotFoundError as exc:
            raise RuntimeError("asset content is missing from object storage") from exc

    headers = {"Content-Disposition": f'attachment; filename="{asset.filename}"'}
    return StreamingResponse(stream(), media_type=asset.mime_type, headers=headers)


def _parse_metadata(value: str | None) -> dict[str, object]:
    if value is None:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="source_metadata must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="source_metadata must be a JSON object")
    return parsed
