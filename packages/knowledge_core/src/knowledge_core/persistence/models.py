from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.persistence.base import Base


def uuid_column() -> Mapped[UUID]:
    return mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def json_column() -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = uuid_column()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class OrganizationRecord(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectRecord(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="status"),
        ForeignKeyConstraint(
            ["default_knowledge_scope_id"],
            ["knowledge_scopes.id"],
            name="fk_projects_default_knowledge_scope_id_knowledge_scopes",
            ondelete="SET NULL",
            use_alter=True,
        ),
        Index(
            "uq_projects_owner_slug",
            "created_by_user_id",
            "slug",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
        Index(
            "uq_projects_organization_slug",
            "organization_id",
            "slug",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_column()
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    default_knowledge_scope_id: Mapped[UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectMembershipRecord(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        PrimaryKeyConstraint("project_id", "user_id"),
        CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="role"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class KnowledgeScopeRecord(Base):
    __tablename__ = "knowledge_scopes"
    __table_args__ = (
        CheckConstraint(
            "(scope_type = 'user_global' AND owner_user_id IS NOT NULL "
            "AND owner_organization_id IS NULL AND project_id IS NULL) OR "
            "(scope_type = 'organization_global' AND owner_user_id IS NULL "
            "AND owner_organization_id IS NOT NULL AND project_id IS NULL) OR "
            "(scope_type = 'project' AND owner_user_id IS NULL "
            "AND owner_organization_id IS NULL AND project_id IS NOT NULL)",
            name="matching_owner",
        ),
        CheckConstraint("visibility IN ('private', 'project', 'organization')", name="visibility"),
        Index(
            "uq_knowledge_scopes_project",
            "project_id",
            unique=True,
            postgresql_where=text("scope_type = 'project'"),
        ),
    )

    id: Mapped[UUID] = uuid_column()
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ConversationRecord(Base):
    __tablename__ = "conversations"
    __table_args__ = (CheckConstraint("status IN ('active', 'archived')", name="status"),)

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class MessageRecord(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="role"),
        CheckConstraint("content_format IN ('markdown', 'plain_text', 'json')", name="format"),
        CheckConstraint("sequence >= 0", name="sequence"),
        UniqueConstraint("conversation_id", "sequence"),
    )

    id: Mapped[UUID] = uuid_column()
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="markdown"
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    research_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="SET NULL")
    )
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()


class AgentTaskRecord(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('chat_answer', 'ingest_source', 'deepen_source', "
            "'extract_memory', 'deep_research', 'report_generation', 'report_edit')",
            name="task_type",
        ),
        CheckConstraint(
            "status IN ('created', 'queued', 'running', 'awaiting_intervention', "
            "'completed', 'failed', 'cancelled')",
            name="status",
        ),
    )

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), index=True
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="created")
    settings: Mapped[dict[str, Any]] = json_column()
    result_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ResearchRunRecord(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'planning', 'awaiting_intervention', 'researching', "
            "'writing', 'editing', 'completed', 'failed', 'cancelled')",
            name="status",
        ),
        CheckConstraint("depth IN ('quick', 'standard', 'deep')", name="depth"),
        CheckConstraint(
            "strategy IN ('breadth_first', 'depth_first', 'hybrid')", name="strategy"
        ),
        CheckConstraint(
            "output_format IN ('markdown', 'report', 'deck_later')", name="output_format"
        ),
        UniqueConstraint("agent_task_id"),
    )

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="created")
    depth: Mapped[str] = mapped_column(String(30), nullable=False, server_default="standard")
    strategy: Mapped[str] = mapped_column(String(30), nullable=False, server_default="hybrid")
    output_format: Mapped[str] = mapped_column(String(30), nullable=False, server_default="report")
    settings: Mapped[dict[str, Any]] = json_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ProductEventRecord(Base):
    __tablename__ = "product_events"
    __table_args__ = (
        CheckConstraint("sequence >= 0", name="sequence"),
        UniqueConstraint("agent_task_id", "sequence"),
    )

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    research_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="SET NULL")
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict[str, Any]] = json_column()
    source_event_id: Mapped[str | None] = mapped_column(String(300))
    trace_id: Mapped[str | None] = mapped_column(String(300), index=True)
    created_at: Mapped[datetime] = created_at_column()


class DeepAgentsThreadRecord(Base):
    __tablename__ = "deepagents_threads"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'completed', 'failed')", name="status"),
        CheckConstraint(
            "conversation_id IS NOT NULL OR agent_task_id IS NOT NULL "
            "OR research_run_id IS NOT NULL",
            name="owner",
        ),
        Index(
            "uq_deepagents_threads_conversation_default",
            "conversation_id",
            unique=True,
            postgresql_where=text("agent_task_id IS NULL AND research_run_id IS NULL"),
        ),
        Index(
            "uq_deepagents_threads_research_run",
            "research_run_id",
            unique=True,
            postgresql_where=text("research_run_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE")
    )
    research_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    thread_id: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    checkpoint_namespace: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class InterventionRequestRecord(Base):
    __tablename__ = "intervention_requests"
    __table_args__ = (
        CheckConstraint(
            "type IN ('topic_approval', 'tool_approval', 'memory_write', "
            "'filesystem_write', 'export_approval')",
            name="type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'edited', 'rejected', 'expired', 'resolved')",
            name="status",
        ),
        CheckConstraint("agent_task_id IS NOT NULL OR research_run_id IS NOT NULL", name="owner"),
        UniqueConstraint("deepagents_thread_id", "checkpoint_id"),
    )

    id: Mapped[UUID] = uuid_column()
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE")
    )
    research_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    deepagents_thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("deepagents_threads.id", ondelete="CASCADE"), nullable=False
    )
    checkpoint_id: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    request_payload: Mapped[dict[str, Any]] = json_column()
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssetRecord(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('upload', 'fetched_source', 'connector_snapshot', 'generated_report', "
            "'chart', 'image', 'code_snapshot', 'export')",
            name="kind",
        ),
        CheckConstraint(
            "status IN ('available', 'processing', 'failed', 'deleted')", name="status"
        ),
        CheckConstraint("size_bytes >= 0", name="size"),
        CheckConstraint("checksum_sha256 ~ '^[0-9a-f]{64}$'", name="checksum_sha256"),
        UniqueConstraint("knowledge_scope_id", "checksum_sha256"),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict[str, Any]] = json_column()
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="available")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class KnowledgeFileRecord(Base):
    __tablename__ = "knowledge_files"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('source_card', 'topic_card', 'repository_card', 'image_card', "
            "'research_map', 'report_section', 'scratch_note')",
            name="file_type",
        ),
        CheckConstraint("status IN ('active', 'stale', 'superseded', 'archived')", name="status"),
        CheckConstraint("created_by IN ('user', 'agent', 'system')", name="creator"),
        UniqueConstraint("knowledge_scope_id", "path"),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    frontmatter: Mapped[dict[str, Any]] = json_column()
    content_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    created_by: Mapped[str] = mapped_column(String(20), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class GraphSchemaVersionRecord(Base):
    __tablename__ = "graph_schema_versions"
    __table_args__ = (
        CheckConstraint("object_kind IN ('node', 'edge', 'candidate')", name="object_kind"),
        CheckConstraint("status IN ('draft', 'active', 'retired')", name="status"),
        CheckConstraint("version > 0", name="version"),
        UniqueConstraint("object_kind", "type_name", "version"),
    )

    id: Mapped[UUID] = uuid_column()
    object_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    json_schema: Mapped[dict[str, Any]] = json_column()
    allowed_from_types: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    allowed_to_types: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    promotion_policy: Mapped[dict[str, Any]] = json_column()
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = created_at_column()


class GraphNodeRecord(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'corrected', 'superseded', 'retracted', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="validity",
        ),
        ForeignKeyConstraint(
            ["schema_object_kind", "type", "schema_version"],
            [
                "graph_schema_versions.object_kind",
                "graph_schema_versions.type_name",
                "graph_schema_versions.version",
            ],
            ondelete="RESTRICT",
        ),
        Index(
            "uq_graph_nodes_scope_canonical_key",
            "knowledge_scope_id",
            "canonical_key",
            unique=True,
            postgresql_where=text("canonical_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_object_kind: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="node"
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text)
    canonical_key: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    knowledge_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_files.id", ondelete="SET NULL")
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    metadata_json: Mapped[dict[str, Any]] = json_column()
    ingestion_level: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_revision: Mapped[str | None] = mapped_column(String(300))
    superseded_by_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class GraphEdgeRecord(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence"
        ),
        CheckConstraint(
            "status IN ('active', 'corrected', 'superseded', 'retracted', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "extraction_method IN ('deterministic', 'parser', 'model', 'user')",
            name="extraction_method",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="validity",
        ),
        ForeignKeyConstraint(
            ["schema_object_kind", "relation", "schema_version"],
            [
                "graph_schema_versions.object_kind",
                "graph_schema_versions.type_name",
                "graph_schema_versions.version",
            ],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    from_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation: Mapped[str] = mapped_column(String(100), nullable=False)
    to_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    schema_object_kind: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="edge"
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    extraction_method: Mapped[str] = mapped_column(String(30), nullable=False)
    extraction_policy_version: Mapped[str | None] = mapped_column(String(100))
    source_revision: Mapped[str | None] = mapped_column(String(300))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class GraphChunkRecord(Base):
    __tablename__ = "graph_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="chunk_index"),
        CheckConstraint(
            "page_end IS NULL OR page_start IS NULL OR page_end >= page_start", name="pages"
        ),
        CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start", name="characters"
        ),
        CheckConstraint(
            "line_end IS NULL OR line_start IS NULL OR line_end >= line_start", name="lines"
        ),
        UniqueConstraint("node_id", "source_revision", "chunk_index"),
        Index(
            "ix_graph_chunks_text_search",
            text("to_tsvector('english', text_content)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_files.id", ondelete="SET NULL")
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(300), nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    char_start: Mapped[int | None] = mapped_column(BigInteger)
    char_end: Mapped[int | None] = mapped_column(BigInteger)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    bounding_boxes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sheet_name: Mapped[str | None] = mapped_column(String(300))
    cell_range: Mapped[str | None] = mapped_column(String(100))
    repository: Mapped[str | None] = mapped_column(Text)
    commit_sha: Mapped[str | None] = mapped_column(String(100))
    file_path: Mapped[str | None] = mapped_column(Text)
    symbol: Mapped[str | None] = mapped_column(Text)
    external_permalink: Mapped[str | None] = mapped_column(Text)
    external_item_id: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String(100))
    parser_version: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class IngestionRunRecord(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('shallow_card', 'section_indexed', 'topic_deepened', "
            "'claims_and_citations', 'code_symbol_trace')",
            name="mode",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="status",
        ),
        CheckConstraint("asset_id IS NOT NULL OR target_node_id IS NOT NULL", name="target"),
    )

    id: Mapped[UUID] = uuid_column()
    knowledge_scope_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_scopes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), index=True
    )
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    target_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="queued")
    coverage: Mapped[dict[str, Any]] = json_column()
    budget: Mapped[dict[str, Any]] = json_column()
    extractor_versions: Mapped[dict[str, Any]] = json_column()
    source_revision: Mapped[str | None] = mapped_column(String(300))
    result_summary: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()
