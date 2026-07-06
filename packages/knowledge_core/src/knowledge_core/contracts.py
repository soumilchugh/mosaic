from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContractModel(BaseModel):
    """Base configuration shared by product-facing contracts."""

    model_config = ConfigDict(extra="forbid")


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeScopeType(StrEnum):
    USER_GLOBAL = "user_global"
    ORGANIZATION_GLOBAL = "organization_global"
    PROJECT = "project"


class KnowledgeScopeVisibility(StrEnum):
    PRIVATE = "private"
    PROJECT = "project"
    ORGANIZATION = "organization"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentTaskType(StrEnum):
    CHAT_ANSWER = "chat_answer"
    INGEST_SOURCE = "ingest_source"
    DEEPEN_SOURCE = "deepen_source"
    EXTRACT_MEMORY = "extract_memory"
    DEEP_RESEARCH = "deep_research"
    REPORT_GENERATION = "report_generation"
    REPORT_EDIT = "report_edit"


class AgentTaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_INTERVENTION = "awaiting_intervention"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetKind(StrEnum):
    UPLOAD = "upload"
    FETCHED_SOURCE = "fetched_source"
    CONNECTOR_SNAPSHOT = "connector_snapshot"
    GENERATED_REPORT = "generated_report"
    CHART = "chart"
    IMAGE = "image"
    CODE_SNAPSHOT = "code_snapshot"
    EXPORT = "export"


class KnowledgeFileType(StrEnum):
    SOURCE_CARD = "source_card"
    TOPIC_CARD = "topic_card"
    REPOSITORY_CARD = "repository_card"
    IMAGE_CARD = "image_card"
    RESEARCH_MAP = "research_map"
    REPORT_SECTION = "report_section"
    SCRATCH_NOTE = "scratch_note"


class KnowledgeFileStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class Project(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    created_by_user_id: UUID
    default_knowledge_scope_id: UUID | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeScope(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    scope_type: KnowledgeScopeType
    name: str = Field(min_length=1, max_length=200)
    visibility: KnowledgeScopeVisibility
    owner_user_id: UUID | None = None
    owner_organization_id: UUID | None = None
    project_id: UUID | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_owner(self) -> Self:
        required_owner = {
            KnowledgeScopeType.USER_GLOBAL: self.owner_user_id,
            KnowledgeScopeType.ORGANIZATION_GLOBAL: self.owner_organization_id,
            KnowledgeScopeType.PROJECT: self.project_id,
        }[self.scope_type]
        if required_owner is None:
            raise ValueError(f"{self.scope_type.value} scope requires its matching owner ID")
        return self


class Conversation(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    created_by_user_id: UUID
    title: str | None = Field(default=None, max_length=300)
    summary: str | None = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Message(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AgentTask(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    conversation_id: UUID | None = None
    created_by_user_id: UUID | None = None
    task_type: AgentTaskType
    intent: str = Field(min_length=1)
    status: AgentTaskStatus = AgentTaskStatus.CREATED
    settings: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProductEvent(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    agent_task_id: UUID
    sequence: int = Field(ge=0)
    type: str = Field(min_length=1, max_length=200)
    conversation_id: UUID | None = None
    research_run_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source_event_id: str | None = None
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Asset(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    kind: AssetKind
    filename: str = Field(min_length=1, max_length=1024)
    mime_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    storage_uri: str = Field(min_length=1)
    project_id: UUID | None = None
    conversation_id: UUID | None = None
    agent_task_id: UUID | None = None
    created_by_user_id: UUID | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgeFile(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    path: str = Field(min_length=1, max_length=2048)
    file_type: KnowledgeFileType
    title: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(min_length=1, max_length=200)
    project_id: UUID | None = None
    asset_id: UUID | None = None
    status: KnowledgeFileStatus = KnowledgeFileStatus.ACTIVE
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
