from datetime import UTC, datetime
from decimal import Decimal
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


class MessageContentFormat(StrEnum):
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    JSON = "json"


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


class ResearchRunStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    AWAITING_INTERVENTION = "awaiting_intervention"
    RESEARCHING = "researching"
    WRITING = "writing"
    EDITING = "editing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchDepth(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class ResearchStrategy(StrEnum):
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    HYBRID = "hybrid"


class ResearchOutputFormat(StrEnum):
    MARKDOWN = "markdown"
    REPORT = "report"
    DECK_LATER = "deck_later"


class DeepAgentsThreadStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class InterventionType(StrEnum):
    TOPIC_APPROVAL = "topic_approval"
    TOOL_APPROVAL = "tool_approval"
    MEMORY_WRITE = "memory_write"
    FILESYSTEM_WRITE = "filesystem_write"
    EXPORT_APPROVAL = "export_approval"


class InterventionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RESOLVED = "resolved"


class AssetKind(StrEnum):
    UPLOAD = "upload"
    FETCHED_SOURCE = "fetched_source"
    CONNECTOR_SNAPSHOT = "connector_snapshot"
    GENERATED_REPORT = "generated_report"
    CHART = "chart"
    IMAGE = "image"
    CODE_SNAPSHOT = "code_snapshot"
    EXPORT = "export"


class AssetStatus(StrEnum):
    AVAILABLE = "available"
    PROCESSING = "processing"
    FAILED = "failed"
    DELETED = "deleted"


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


class GraphRecordStatus(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    ARCHIVED = "archived"


class IngestionRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    content_format: MessageContentFormat = MessageContentFormat.MARKDOWN
    user_id: UUID | None = None
    research_run_id: UUID | None = None
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


class ResearchRun(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    conversation_id: UUID
    agent_task_id: UUID
    created_by_user_id: UUID | None = None
    intent: str = Field(min_length=1)
    status: ResearchRunStatus = ResearchRunStatus.CREATED
    depth: ResearchDepth = ResearchDepth.STANDARD
    strategy: ResearchStrategy = ResearchStrategy.HYBRID
    output_format: ResearchOutputFormat = ResearchOutputFormat.REPORT
    settings: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DeepAgentsThread(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    thread_id: str = Field(min_length=1, max_length=300)
    conversation_id: UUID | None = None
    agent_task_id: UUID | None = None
    research_run_id: UUID | None = None
    checkpoint_namespace: str | None = Field(default=None, max_length=300)
    status: DeepAgentsThreadStatus = DeepAgentsThreadStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_owner(self) -> Self:
        if not any((self.conversation_id, self.agent_task_id, self.research_run_id)):
            raise ValueError("a DeepAgents thread requires a product owner")
        return self


class InterventionRequest(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    deepagents_thread_id: UUID
    checkpoint_id: str = Field(min_length=1, max_length=500)
    type: InterventionType
    conversation_id: UUID | None = None
    agent_task_id: UUID | None = None
    research_run_id: UUID | None = None
    status: InterventionStatus = InterventionStatus.PENDING
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] | None = None
    requested_at: datetime = Field(default_factory=utc_now)
    responded_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_owner(self) -> Self:
        if self.agent_task_id is None and self.research_run_id is None:
            raise ValueError("an intervention requires an agent task or research run")
        return self


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
    source_url: str | None = None
    project_id: UUID | None = None
    conversation_id: UUID | None = None
    agent_task_id: UUID | None = None
    created_by_user_id: UUID | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    status: AssetStatus = AssetStatus.AVAILABLE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeFile(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    path: str = Field(min_length=1, max_length=2048)
    file_type: KnowledgeFileType
    title: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(min_length=1, max_length=200)
    project_id: UUID | None = None
    conversation_id: UUID | None = None
    asset_id: UUID | None = None
    status: KnowledgeFileStatus = KnowledgeFileStatus.ACTIVE
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "agent"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GraphSchemaVersion(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    object_kind: str
    type_name: str
    version: int = Field(gt=0)
    json_schema: dict[str, Any] = Field(default_factory=dict)
    allowed_from_types: list[str] | None = None
    allowed_to_types: list[str] | None = None
    promotion_policy: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    created_at: datetime = Field(default_factory=utc_now)


class GraphNode(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    project_id: UUID
    type: str
    schema_version: int = Field(gt=0)
    schema_object_kind: str = "node"
    external_id: str | None = None
    canonical_key: str | None = None
    title: str | None = None
    summary: str | None = None
    knowledge_file_id: UUID | None = None
    asset_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingestion_level: str | None = None
    status: GraphRecordStatus = GraphRecordStatus.ACTIVE
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source_revision: str | None = None
    superseded_by_node_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GraphEdge(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    project_id: UUID
    from_node_id: UUID
    relation: str
    to_node_id: UUID
    schema_version: int = Field(gt=0)
    schema_object_kind: str = "edge"
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    status: GraphRecordStatus = GraphRecordStatus.ACTIVE
    extraction_method: str
    extraction_policy_version: str | None = None
    source_revision: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GraphChunk(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    project_id: UUID
    node_id: UUID
    chunk_index: int = Field(ge=0)
    source_revision: str
    text_content: str
    content_hash: str
    knowledge_file_id: UUID | None = None
    asset_id: UUID | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_path: list[str] | None = None
    char_start: int | None = None
    char_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    bounding_boxes: dict[str, Any] | None = None
    sheet_name: str | None = None
    cell_range: str | None = None
    repository: str | None = None
    commit_sha: str | None = None
    file_path: str | None = None
    symbol: str | None = None
    external_permalink: str | None = None
    external_item_id: str | None = None
    parser_name: str | None = None
    parser_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IngestionRun(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    knowledge_scope_id: UUID
    project_id: UUID
    mode: str
    agent_task_id: UUID | None = None
    asset_id: UUID | None = None
    target_node_id: UUID | None = None
    status: IngestionRunStatus = IngestionRunStatus.QUEUED
    coverage: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    extractor_versions: dict[str, Any] = Field(default_factory=dict)
    source_revision: str | None = None
    result_summary: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if self.asset_id is None and self.target_node_id is None:
            raise ValueError("an ingestion run requires an asset or target node")
        return self
