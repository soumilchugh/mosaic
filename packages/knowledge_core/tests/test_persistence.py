import os
from uuid import uuid4

import pytest
from knowledge_core.persistence import (
    AgentTaskRecord,
    AssetRecord,
    Base,
    ConversationRecord,
    GraphChunkRecord,
    GraphNodeRecord,
    GraphSchemaVersionRecord,
    IngestionRunRecord,
    KnowledgeScopeRecord,
    MessageRecord,
    ProductEventRecord,
    ProjectMembershipRecord,
    ProjectRecord,
    UserRecord,
)
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

CORE_TABLES = {
    "agent_tasks",
    "assets",
    "conversations",
    "deepagents_threads",
    "graph_chunks",
    "graph_edges",
    "graph_nodes",
    "graph_schema_versions",
    "ingestion_runs",
    "knowledge_files",
    "knowledge_scopes",
    "messages",
    "organizations",
    "product_events",
    "project_memberships",
    "projects",
    "users",
}


def test_metadata_declares_the_core_platform_schema() -> None:
    assert CORE_TABLES == set(Base.metadata.tables)


@pytest.mark.skipif(
    not os.getenv("MOSAIC_TEST_DATABASE_URL"),
    reason="MOSAIC_TEST_DATABASE_URL is required for the PostgreSQL integration test",
)
def test_migrated_schema_persists_the_first_knowledge_workflow() -> None:
    engine = create_engine(os.environ["MOSAIC_TEST_DATABASE_URL"])
    assert CORE_TABLES <= set(inspect(engine).get_table_names())
    suffix = uuid4().hex
    project_slug = f"migration-test-{suffix}"
    checksum = suffix * 2
    chunk_hash = f"sha256:{suffix}"

    with Session(engine) as session, session.begin():
        user = UserRecord(email=f"schema-test-{suffix}@mosaic.local", display_name="Schema Test")
        session.add(user)
        session.flush()

        project = ProjectRecord(
            name="Migration test",
            slug=project_slug,
            created_by_user_id=user.id,
        )
        session.add(project)
        session.flush()

        scope = KnowledgeScopeRecord(
            scope_type="project",
            project_id=project.id,
            name="Migration test knowledge",
            visibility="project",
        )
        session.add(scope)
        session.flush()
        project.default_knowledge_scope_id = scope.id

        session.add(ProjectMembershipRecord(project_id=project.id, user_id=user.id, role="owner"))
        conversation = ConversationRecord(
            project_id=project.id,
            created_by_user_id=user.id,
            title="First conversation",
        )
        session.add(conversation)
        session.flush()

        session.add(
            MessageRecord(
                conversation_id=conversation.id,
                role="user",
                content="What is in this source?",
                sequence=0,
                user_id=user.id,
            )
        )
        task = AgentTaskRecord(
            project_id=project.id,
            conversation_id=conversation.id,
            created_by_user_id=user.id,
            task_type="ingest_source",
            intent="Index the uploaded source",
        )
        session.add(task)
        session.flush()
        session.add(
            ProductEventRecord(
                project_id=project.id,
                conversation_id=conversation.id,
                agent_task_id=task.id,
                sequence=0,
                type="run.created",
            )
        )

        asset = AssetRecord(
            knowledge_scope_id=scope.id,
            project_id=project.id,
            conversation_id=conversation.id,
            agent_task_id=task.id,
            created_by_user_id=user.id,
            kind="upload",
            filename="brief.md",
            mime_type="text/markdown",
            size_bytes=24,
            checksum_sha256=checksum,
            storage_uri="object://project/brief.md",
        )
        session.add(asset)
        session.flush()

        schema = GraphSchemaVersionRecord(
            object_kind="node",
            type_name=f"source_{suffix}",
            version=1,
            json_schema={"type": "object"},
            status="active",
        )
        session.add(schema)
        session.flush()
        node = GraphNodeRecord(
            knowledge_scope_id=scope.id,
            project_id=project.id,
            type=f"source_{suffix}",
            schema_version=1,
            canonical_key=f"asset:{asset.id}",
            title="Brief",
            asset_id=asset.id,
            ingestion_level="shallow_card",
        )
        session.add(node)
        session.flush()

        session.add(
            GraphChunkRecord(
                knowledge_scope_id=scope.id,
                project_id=project.id,
                node_id=node.id,
                asset_id=asset.id,
                chunk_index=0,
                source_revision=f"sha256:{checksum}",
                text_content="Mosaic connects durable knowledge to source evidence.",
                content_hash=chunk_hash,
            )
        )
        session.add(
            IngestionRunRecord(
                knowledge_scope_id=scope.id,
                project_id=project.id,
                agent_task_id=task.id,
                asset_id=asset.id,
                target_node_id=node.id,
                mode="shallow_card",
            )
        )

    with Session(engine) as session:
        persisted_project = session.scalar(
            select(ProjectRecord).where(ProjectRecord.slug == project_slug)
        )
        assert persisted_project is not None
        assert persisted_project.default_knowledge_scope_id is not None
        persisted_chunk = session.scalar(
            select(GraphChunkRecord).where(GraphChunkRecord.content_hash == chunk_hash)
        )
        assert persisted_chunk is not None
        assert persisted_chunk.text_content.startswith("Mosaic")

    engine.dispose()
