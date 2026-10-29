import os
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from knowledge_core import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskType,
    Asset,
    AssetKind,
    Conversation,
    GraphChunk,
    GraphEdge,
    GraphNode,
    GraphSchemaVersion,
    IngestionRun,
    KnowledgeFile,
    KnowledgeFileType,
    Message,
    MessageRole,
    ProductEvent,
    Project,
)
from knowledge_core.persistence import (
    InMemoryProjectRepository,
    InMemoryRepositories,
    InMemoryRepositoryStore,
    KnowledgeScopeRecord,
    ProjectAccessDeniedError,
    ProjectBoundaryError,
    ProjectContext,
    ProjectMembershipRecord,
    SqlAlchemyProjectRepository,
    SqlAlchemyRepositories,
    UserRecord,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class WorkflowIds:
    user_id: UUID
    project_id: UUID
    scope_id: UUID


def make_project(user_id: UUID, suffix: str) -> Project:
    return Project(
        name="Repository test",
        slug=f"repository-test-{suffix}",
        created_by_user_id=user_id,
    )


def exercise_repository_workflow(repositories, ids: WorkflowIds, suffix: str) -> None:
    conversation = repositories.conversations.add(
        Conversation(
            project_id=ids.project_id,
            created_by_user_id=ids.user_id,
            title="Initial title",
        )
    )
    conversation = repositories.conversations.update(
        conversation.model_copy(update={"title": "Updated title"})
    )
    assert repositories.conversations.get(conversation.id).title == "Updated title"
    assert [item.id for item in repositories.conversations.list()] == [conversation.id]

    message = repositories.messages.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="What is in this source?",
            sequence=0,
            user_id=ids.user_id,
        )
    )
    message = repositories.messages.update(
        message.model_copy(update={"content": "What evidence is in this source?"})
    )
    assert repositories.messages.get(message.id).content.startswith("What evidence")
    assert [item.id for item in repositories.messages.list()] == [message.id]

    task = repositories.tasks.add(
        AgentTask(
            project_id=ids.project_id,
            conversation_id=conversation.id,
            created_by_user_id=ids.user_id,
            task_type=AgentTaskType.INGEST_SOURCE,
            intent="Index the source",
        )
    )
    task = repositories.tasks.update(task.model_copy(update={"status": AgentTaskStatus.RUNNING}))
    assert repositories.tasks.get(task.id).status == AgentTaskStatus.RUNNING
    event = repositories.events.add(
        ProductEvent(
            project_id=ids.project_id,
            conversation_id=conversation.id,
            agent_task_id=task.id,
            sequence=0,
            type="run.created",
        )
    )
    event = repositories.events.update(event.model_copy(update={"payload": {"step": "ingest"}}))
    assert repositories.events.get(event.id).payload == {"step": "ingest"}

    checksum = suffix.ljust(64, "0")[:64]
    asset = repositories.assets.add(
        Asset(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            conversation_id=conversation.id,
            agent_task_id=task.id,
            created_by_user_id=ids.user_id,
            kind=AssetKind.UPLOAD,
            filename="brief.md",
            mime_type="text/markdown",
            size_bytes=42,
            checksum_sha256=checksum,
            storage_uri=f"object://repository-test/{suffix}/brief.md",
        )
    )
    asset = repositories.assets.update(asset.model_copy(update={"filename": "updated-brief.md"}))
    assert repositories.assets.get(asset.id).filename == "updated-brief.md"
    knowledge_file = repositories.knowledge_files.add(
        KnowledgeFile(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            conversation_id=conversation.id,
            asset_id=asset.id,
            path=f"sources/{suffix}.md",
            file_type=KnowledgeFileType.SOURCE_CARD,
            title="Brief",
            content_hash=f"sha256:{suffix}",
        )
    )
    knowledge_file = repositories.knowledge_files.update(
        knowledge_file.model_copy(update={"title": "Updated brief"})
    )
    assert repositories.knowledge_files.get(knowledge_file.id).asset_id == asset.id

    node_schema = repositories.graph_schemas.add(
        GraphSchemaVersion(
            object_kind="node",
            type_name=f"source_{suffix}",
            version=1,
            status="active",
        )
    )
    node_schema = repositories.graph_schemas.update(
        node_schema.model_copy(update={"promotion_policy": {"evidence_required": True}})
    )
    repositories.graph_schemas.add(
        GraphSchemaVersion(
            object_kind="edge",
            type_name=f"references_{suffix}",
            version=1,
            status="active",
        )
    )
    assert repositories.graph_schemas.get(node_schema.id).promotion_policy == {
        "evidence_required": True
    }

    source_node = repositories.graph_nodes.add(
        GraphNode(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            type=f"source_{suffix}",
            schema_version=1,
            canonical_key=f"asset:{asset.id}",
            title="Brief",
            asset_id=asset.id,
            knowledge_file_id=knowledge_file.id,
            ingestion_level="shallow_card",
        )
    )
    source_node = repositories.graph_nodes.update(
        source_node.model_copy(update={"summary": "A shallow source card."})
    )
    topic_node = repositories.graph_nodes.add(
        GraphNode(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            type=f"source_{suffix}",
            schema_version=1,
            canonical_key=f"topic:{suffix}",
            title="Mosaic",
        )
    )
    edge = repositories.graph_edges.add(
        GraphEdge(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            from_node_id=source_node.id,
            relation=f"references_{suffix}",
            to_node_id=topic_node.id,
            schema_version=1,
            extraction_method="model",
        )
    )
    edge = repositories.graph_edges.update(
        edge.model_copy(update={"metadata": {"evidence": "chunk:0"}})
    )
    chunk = repositories.graph_chunks.add(
        GraphChunk(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            node_id=source_node.id,
            asset_id=asset.id,
            knowledge_file_id=knowledge_file.id,
            chunk_index=0,
            source_revision=f"sha256:{checksum}",
            text_content="Mosaic connects durable knowledge to evidence.",
            content_hash=f"sha256:chunk-{suffix}",
        )
    )
    chunk = repositories.graph_chunks.update(
        chunk.model_copy(update={"metadata": {"language": "en"}})
    )
    run = repositories.ingestion_runs.add(
        IngestionRun(
            knowledge_scope_id=ids.scope_id,
            project_id=ids.project_id,
            agent_task_id=task.id,
            asset_id=asset.id,
            target_node_id=source_node.id,
            mode="shallow_card",
        )
    )
    run = repositories.ingestion_runs.update(run.model_copy(update={"coverage": {"chunks": 1}}))

    assert repositories.graph_nodes.get(source_node.id).summary == "A shallow source card."
    assert repositories.graph_edges.get(edge.id).metadata == {"evidence": "chunk:0"}
    assert repositories.graph_chunks.get(chunk.id).metadata == {"language": "en"}
    assert repositories.ingestion_runs.get(run.id).coverage == {"chunks": 1}
    assert len(repositories.graph_nodes.list()) == 2


def test_in_memory_repositories_support_the_first_knowledge_workflow() -> None:
    owner_id = uuid4()
    project = make_project(owner_id, uuid4().hex)
    scope_id = uuid4()
    store = InMemoryRepositoryStore()
    InMemoryProjectRepository(store, owner_id).add(project)
    store.register_knowledge_scope(scope_id, project.id)

    repositories = InMemoryRepositories(store, ProjectContext(project.id, owner_id))
    exercise_repository_workflow(
        repositories,
        WorkflowIds(owner_id, project.id, scope_id),
        uuid4().hex,
    )


def test_in_memory_repositories_enforce_user_project_and_scope_boundaries() -> None:
    owner_id = uuid4()
    member_id = uuid4()
    outsider_id = uuid4()
    first_project = make_project(owner_id, uuid4().hex)
    second_project = make_project(owner_id, uuid4().hex)
    first_scope_id = uuid4()
    second_scope_id = uuid4()
    store = InMemoryRepositoryStore()
    projects = InMemoryProjectRepository(store, owner_id)
    projects.add(first_project)
    projects.add(second_project)
    store.grant_project_access(first_project.id, member_id)
    store.register_knowledge_scope(first_scope_id, first_project.id)
    store.register_knowledge_scope(second_scope_id, second_project.id)

    InMemoryRepositories(store, ProjectContext(first_project.id, member_id))
    with pytest.raises(ProjectAccessDeniedError):
        InMemoryRepositories(store, ProjectContext(first_project.id, outsider_id))

    repositories = InMemoryRepositories(store, ProjectContext(first_project.id, owner_id))
    foreign_conversation = InMemoryRepositories(
        store, ProjectContext(second_project.id, owner_id)
    ).conversations.add(Conversation(project_id=second_project.id, created_by_user_id=owner_id))
    with pytest.raises(ProjectBoundaryError):
        repositories.conversations.add(
            Conversation(project_id=second_project.id, created_by_user_id=owner_id)
        )
    with pytest.raises(ProjectBoundaryError):
        repositories.tasks.add(
            AgentTask(
                project_id=first_project.id,
                conversation_id=foreign_conversation.id,
                task_type=AgentTaskType.CHAT_ANSWER,
                intent="Cross a project boundary",
            )
        )
    with pytest.raises(ProjectBoundaryError):
        repositories.assets.add(
            Asset(
                knowledge_scope_id=second_scope_id,
                project_id=first_project.id,
                kind=AssetKind.UPLOAD,
                filename="foreign.md",
                mime_type="text/markdown",
                size_bytes=1,
                checksum_sha256="a" * 64,
                storage_uri="object://foreign.md",
            )
        )


@pytest.mark.skipif(
    not os.getenv("MOSAIC_TEST_DATABASE_URL"),
    reason="MOSAIC_TEST_DATABASE_URL is required for the PostgreSQL integration test",
)
def test_sqlalchemy_repositories_match_the_in_memory_workflow_and_boundaries() -> None:
    engine = create_engine(os.environ["MOSAIC_TEST_DATABASE_URL"])
    suffix = uuid4().hex
    owner_id = uuid4()
    outsider_id = uuid4()
    member_id = uuid4()
    scope_id = uuid4()

    with Session(engine) as session, session.begin():
        session.add_all(
            [
                UserRecord(id=owner_id, email=f"repository-owner-{suffix}@mosaic.local"),
                UserRecord(id=outsider_id, email=f"repository-outsider-{suffix}@mosaic.local"),
                UserRecord(id=member_id, email=f"repository-member-{suffix}@mosaic.local"),
            ]
        )
        session.flush()
        project = SqlAlchemyProjectRepository(session, owner_id).add(make_project(owner_id, suffix))
        session.add(
            KnowledgeScopeRecord(
                id=scope_id,
                scope_type="project",
                project_id=project.id,
                name="Repository test knowledge",
                visibility="project",
            )
        )
        session.add(
            ProjectMembershipRecord(project_id=project.id, user_id=member_id, role="viewer")
        )
        session.flush()

        with pytest.raises(ProjectAccessDeniedError):
            SqlAlchemyRepositories(session, ProjectContext(project.id, outsider_id))
        SqlAlchemyRepositories(session, ProjectContext(project.id, member_id))

        repositories = SqlAlchemyRepositories(session, ProjectContext(project.id, owner_id))
        exercise_repository_workflow(
            repositories,
            WorkflowIds(owner_id, project.id, scope_id),
            suffix,
        )

    engine.dispose()
