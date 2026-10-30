from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from knowledge_core import (
    AgentTask,
    AgentTaskType,
    AssetKind,
    AssetService,
    CreateAsset,
    FilesystemObjectStorage,
    InvalidObjectKeyError,
    ObjectNotFoundError,
    Project,
    safe_filename,
)
from knowledge_core.persistence import (
    InMemoryRepositories,
    InMemoryRepositoryStore,
    ProjectContext,
)


def make_service(tmp_path: Path) -> tuple[AssetService, InMemoryRepositories, dict[str, object]]:
    owner_id = uuid4()
    project = Project(
        name="Storage test",
        slug=f"storage-test-{uuid4().hex}",
        created_by_user_id=owner_id,
    )
    scope_id = uuid4()
    store = InMemoryRepositoryStore(projects={project.id: project})
    store.register_knowledge_scope(scope_id, project.id)
    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    storage = FilesystemObjectStorage(tmp_path / "objects", "test-assets")
    return (
        AssetService(repositories, storage),
        repositories,
        {"owner_id": owner_id, "project_id": project.id, "scope_id": scope_id},
    )


def command(ids: dict[str, object], **overrides: object) -> CreateAsset:
    values = {
        "knowledge_scope_id": ids["scope_id"],
        "project_id": ids["project_id"],
        "created_by_user_id": ids["owner_id"],
        "kind": AssetKind.UPLOAD,
        "filename": "brief.md",
        "mime_type": "text/markdown",
    }
    values.update(overrides)
    return CreateAsset(**values)


def test_filesystem_storage_round_trip_and_key_validation(tmp_path: Path) -> None:
    storage = FilesystemObjectStorage(tmp_path, "assets")
    content = b"durable evidence"

    stored = storage.put("scope/asset/evidence.txt", BytesIO(content))

    assert stored.size_bytes == len(content)
    assert stored.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert stored.uri == "object://assets/scope/asset/evidence.txt"
    with storage.open(stored.uri) as source:
        assert source.read() == content

    with pytest.raises(InvalidObjectKeyError):
        storage.put("../escape.txt", BytesIO(b"no"))
    with pytest.raises(InvalidObjectKeyError):
        storage.open("object://another-bucket/file.txt").__enter__()
    with pytest.raises(ValueError, match="bucket"):
        FilesystemObjectStorage(tmp_path, "../escape")

    storage.delete(stored.uri)
    with pytest.raises(ObjectNotFoundError):
        with storage.open(stored.uri):
            pass


@pytest.mark.parametrize(
    ("provided", "expected"),
    [
        ("../private/report.pdf", "report.pdf"),
        (r"C:\\uploads\\chart?.png", "chart_.png"),
        (" spaced source .md ", "spaced source .md"),
    ],
)
def test_safe_filename_removes_paths_and_unsafe_characters(
    provided: str, expected: str
) -> None:
    assert safe_filename(provided) == expected


def test_asset_service_stores_metadata_content_and_workspace_copy(tmp_path: Path) -> None:
    service, repositories, ids = make_service(tmp_path)
    content = b"# Source\n\nThe relevant evidence."

    asset = service.create(command(ids, filename="../source.md"), BytesIO(content))

    assert repositories.assets.get(asset.id) == asset
    assert asset.filename == "source.md"
    assert asset.checksum_sha256 == hashlib.sha256(content).hexdigest()
    with service.open(asset.id) as (opened_asset, source):
        assert opened_asset.id == asset.id
        assert source.read() == content

    seeded = service.seed_workspace([asset], tmp_path / "workspace")
    assert len(seeded) == 1
    assert seeded[0].parent.name == "uploads"
    assert seeded[0].read_bytes() == content
    assert seeded[0].name.endswith("_source.md")


def test_generated_artifact_creates_linked_product_event(tmp_path: Path) -> None:
    service, repositories, ids = make_service(tmp_path)
    task = repositories.tasks.add(
        AgentTask(
            project_id=ids["project_id"],
            created_by_user_id=ids["owner_id"],
            task_type=AgentTaskType.REPORT_GENERATION,
            intent="Generate the report",
        )
    )

    asset, event = service.create_generated_artifact(
        command(
            ids,
            kind=AssetKind.GENERATED_REPORT,
            filename="report.md",
            agent_task_id=task.id,
        ),
        BytesIO(b"# Generated report"),
        event_sequence=4,
    )

    assert event.type == "artifact.generated"
    assert event.agent_task_id == task.id
    assert event.payload["asset_id"] == str(asset.id)
    assert repositories.events.get(event.id) == event


def test_generated_artifact_requires_task(tmp_path: Path) -> None:
    service, _, ids = make_service(tmp_path)

    with pytest.raises(ValueError, match="require an agent task"):
        service.create_generated_artifact(
            command(ids), BytesIO(b"content"), event_sequence=0
        )
