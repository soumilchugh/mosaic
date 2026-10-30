from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from api.assets import get_asset_service
from api.main import create_app
from fastapi.testclient import TestClient
from knowledge_core import AssetService, FilesystemObjectStorage, MosaicSettings, Project
from knowledge_core.persistence import (
    InMemoryRepositories,
    InMemoryRepositoryStore,
    ProjectContext,
)


def test_asset_upload_metadata_and_content_round_trip(tmp_path: Path) -> None:
    owner_id = uuid4()
    project = Project(
        name="API asset test",
        slug=f"api-asset-{uuid4().hex}",
        created_by_user_id=owner_id,
    )
    scope_id = uuid4()
    store = InMemoryRepositoryStore(projects={project.id: project})
    store.register_knowledge_scope(scope_id, project.id)
    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    service = AssetService(
        repositories,
        FilesystemObjectStorage(tmp_path / "objects", "api-assets"),
    )
    app = create_app(MosaicSettings(_env_file=None, storage_root=tmp_path / "configured"))
    app.dependency_overrides[get_asset_service] = lambda: service
    client = TestClient(app)
    headers = {"X-User-Id": str(owner_id)}
    content = b"uploaded through the API"

    response = client.post(
        f"/projects/{project.id}/assets",
        headers=headers,
        data={
            "knowledge_scope_id": str(scope_id),
            "source_metadata": '{"origin":"test"}',
        },
        files={"file": ("notes.txt", content, "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "notes.txt"
    assert payload["size_bytes"] == len(content)
    assert payload["source_metadata"] == {"origin": "test"}

    metadata = client.get(
        f"/projects/{project.id}/assets/{payload['id']}", headers=headers
    )
    downloaded = client.get(
        f"/projects/{project.id}/assets/{payload['id']}/content", headers=headers
    )

    assert metadata.status_code == 200
    assert metadata.json() == payload
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["content-type"] == "text/plain; charset=utf-8"


def test_asset_upload_rejects_non_object_source_metadata(tmp_path: Path) -> None:
    app = create_app(MosaicSettings(_env_file=None, storage_root=tmp_path))
    app.dependency_overrides[get_asset_service] = lambda: object()
    client = TestClient(app)

    response = client.post(
        f"/projects/{uuid4()}/assets",
        headers={"X-User-Id": str(uuid4())},
        data={"knowledge_scope_id": str(uuid4()), "source_metadata": "[]"},
        files={"file": ("notes.txt", b"content", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "source_metadata must be a JSON object"
