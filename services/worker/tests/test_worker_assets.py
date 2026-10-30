from pathlib import Path
from uuid import uuid4

from knowledge_core import AgentTask, AgentTaskType, FilesystemObjectStorage, Project
from knowledge_core.persistence import (
    InMemoryRepositories,
    InMemoryRepositoryStore,
    ProjectContext,
)
from worker.assets import capture_generated_artifact, seed_task_workspace


def test_worker_captures_and_reseeds_generated_artifact(tmp_path: Path) -> None:
    owner_id = uuid4()
    project = Project(
        name="Worker asset test",
        slug=f"worker-assets-{uuid4().hex}",
        created_by_user_id=owner_id,
    )
    scope_id = uuid4()
    store = InMemoryRepositoryStore(projects={project.id: project})
    store.register_knowledge_scope(scope_id, project.id)
    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    task = repositories.tasks.add(
        AgentTask(
            project_id=project.id,
            created_by_user_id=owner_id,
            task_type=AgentTaskType.REPORT_GENERATION,
            intent="Create a report",
        )
    )
    storage = FilesystemObjectStorage(tmp_path / "objects", "worker-assets")
    generated = tmp_path / "artifacts" / "report.md"
    generated.parent.mkdir()
    generated.write_text("# Durable report\n", encoding="utf-8")

    asset, event = capture_generated_artifact(
        repositories,
        storage,
        path=generated,
        knowledge_scope_id=scope_id,
        project_id=project.id,
        agent_task_id=task.id,
        created_by_user_id=owner_id,
        event_sequence=2,
    )
    seeded = seed_task_workspace(
        repositories, storage, [asset.id], tmp_path / "next-workspace"
    )

    assert asset.mime_type == "text/markdown"
    assert event.type == "artifact.generated"
    assert seeded[0].read_text(encoding="utf-8") == "# Durable report\n"
