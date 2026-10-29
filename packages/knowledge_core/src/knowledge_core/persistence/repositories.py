from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from knowledge_core.contracts import (
    AgentTask,
    Asset,
    Conversation,
    GraphChunk,
    GraphEdge,
    GraphNode,
    GraphSchemaVersion,
    IngestionRun,
    KnowledgeFile,
    Message,
    ProductEvent,
    Project,
)
from knowledge_core.persistence.models import (
    AgentTaskRecord,
    AssetRecord,
    ConversationRecord,
    GraphChunkRecord,
    GraphEdgeRecord,
    GraphNodeRecord,
    GraphSchemaVersionRecord,
    IngestionRunRecord,
    KnowledgeFileRecord,
    KnowledgeScopeRecord,
    MessageRecord,
    ProductEventRecord,
    ProjectMembershipRecord,
    ProjectRecord,
)

ContractT = TypeVar("ContractT", bound=BaseModel)
RecordT = TypeVar("RecordT")


class RepositoryError(RuntimeError):
    """Base error for repository operations."""


class EntityNotFoundError(RepositoryError):
    pass


class ProjectAccessDeniedError(RepositoryError):
    pass


class ProjectBoundaryError(RepositoryError):
    pass


@dataclass(frozen=True)
class ProjectContext:
    project_id: UUID
    actor_user_id: UUID | None

    @classmethod
    def for_worker(cls, project_id: UUID) -> ProjectContext:
        return cls(project_id=project_id, actor_user_id=None)


class EntityRepository(Protocol[ContractT]):
    def add(self, entity: ContractT) -> ContractT: ...

    def get(self, entity_id: UUID) -> ContractT: ...

    def list(self) -> list[ContractT]: ...

    def update(self, entity: ContractT) -> ContractT: ...


class PlatformRepositories(Protocol):
    projects: EntityRepository[Project]
    conversations: EntityRepository[Conversation]
    messages: EntityRepository[Message]
    tasks: EntityRepository[AgentTask]
    events: EntityRepository[ProductEvent]
    assets: EntityRepository[Asset]
    knowledge_files: EntityRepository[KnowledgeFile]
    graph_schemas: EntityRepository[GraphSchemaVersion]
    graph_nodes: EntityRepository[GraphNode]
    graph_edges: EntityRepository[GraphEdge]
    graph_chunks: EntityRepository[GraphChunk]
    ingestion_runs: EntityRepository[IngestionRun]


@dataclass(frozen=True)
class _RepositorySpec(Generic[ContractT, RecordT]):
    contract_type: type[ContractT]
    record_type: type[RecordT]
    fields: tuple[str, ...]
    update_fields: tuple[str, ...]
    aliases: dict[str, str] = field(default_factory=dict)

    def record_name(self, field_name: str) -> str:
        return self.aliases.get(field_name, field_name)

    def values(self, entity: ContractT, *, include_id: bool) -> dict[str, Any]:
        values = {
            self.record_name(name): getattr(entity, name)
            for name in self.fields
            if include_id or name != "id"
        }
        return values

    def contract(self, record: RecordT) -> ContractT:
        return self.contract_type.model_validate(
            {name: getattr(record, self.record_name(name)) for name in self.fields}
        )


PROJECT_FIELDS = (
    "id",
    "organization_id",
    "name",
    "slug",
    "created_by_user_id",
    "default_knowledge_scope_id",
    "status",
    "metadata",
    "created_at",
    "updated_at",
)

PROJECT_SPEC = _RepositorySpec(
    Project,
    ProjectRecord,
    PROJECT_FIELDS,
    (
        "organization_id",
        "name",
        "slug",
        "default_knowledge_scope_id",
        "status",
        "metadata",
        "updated_at",
    ),
    {"metadata": "metadata_json"},
)

CONVERSATION_SPEC = _RepositorySpec(
    Conversation,
    ConversationRecord,
    tuple(Conversation.model_fields),
    ("title", "summary", "status", "metadata", "updated_at"),
    {"metadata": "metadata_json"},
)

MESSAGE_SPEC = _RepositorySpec(
    Message,
    MessageRecord,
    tuple(Message.model_fields),
    ("role", "content", "content_format", "user_id", "metadata"),
    {"metadata": "metadata_json"},
)

TASK_SPEC = _RepositorySpec(
    AgentTask,
    AgentTaskRecord,
    tuple(AgentTask.model_fields),
    (
        "conversation_id",
        "task_type",
        "intent",
        "status",
        "settings",
        "result_summary",
        "started_at",
        "completed_at",
        "updated_at",
    ),
)

EVENT_SPEC = _RepositorySpec(
    ProductEvent,
    ProductEventRecord,
    tuple(name for name in ProductEvent.model_fields if name != "research_run_id"),
    ("type", "payload", "source_event_id", "trace_id"),
)

ASSET_SPEC = _RepositorySpec(
    Asset,
    AssetRecord,
    tuple(Asset.model_fields),
    (
        "filename",
        "mime_type",
        "storage_uri",
        "source_url",
        "source_metadata",
        "status",
        "updated_at",
    ),
)

KNOWLEDGE_FILE_SPEC = _RepositorySpec(
    KnowledgeFile,
    KnowledgeFileRecord,
    tuple(KnowledgeFile.model_fields),
    (
        "path",
        "file_type",
        "title",
        "frontmatter",
        "content_hash",
        "status",
        "metadata",
        "updated_at",
    ),
    {"metadata": "metadata_json"},
)

GRAPH_SCHEMA_SPEC = _RepositorySpec(
    GraphSchemaVersion,
    GraphSchemaVersionRecord,
    tuple(GraphSchemaVersion.model_fields),
    (
        "json_schema",
        "allowed_from_types",
        "allowed_to_types",
        "promotion_policy",
        "status",
    ),
)

GRAPH_NODE_SPEC = _RepositorySpec(
    GraphNode,
    GraphNodeRecord,
    tuple(GraphNode.model_fields),
    tuple(
        name
        for name in GraphNode.model_fields
        if name not in {"id", "project_id", "knowledge_scope_id", "created_at"}
    ),
    {"metadata": "metadata_json"},
)

GRAPH_EDGE_SPEC = _RepositorySpec(
    GraphEdge,
    GraphEdgeRecord,
    tuple(GraphEdge.model_fields),
    tuple(
        name
        for name in GraphEdge.model_fields
        if name not in {"id", "project_id", "knowledge_scope_id", "created_at"}
    ),
    {"metadata": "metadata_json"},
)

GRAPH_CHUNK_SPEC = _RepositorySpec(
    GraphChunk,
    GraphChunkRecord,
    tuple(GraphChunk.model_fields),
    tuple(
        name
        for name in GraphChunk.model_fields
        if name not in {"id", "project_id", "knowledge_scope_id", "node_id", "created_at"}
    ),
    {"metadata": "metadata_json"},
)

INGESTION_RUN_SPEC = _RepositorySpec(
    IngestionRun,
    IngestionRunRecord,
    tuple(IngestionRun.model_fields),
    tuple(
        name
        for name in IngestionRun.model_fields
        if name not in {"id", "project_id", "knowledge_scope_id", "created_at"}
    ),
)


def _project_access_filter(user_id: UUID) -> Any:
    membership = exists(
        select(ProjectMembershipRecord.project_id).where(
            ProjectMembershipRecord.project_id == ProjectRecord.id,
            ProjectMembershipRecord.user_id == user_id,
        )
    )
    return or_(ProjectRecord.created_by_user_id == user_id, membership)


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session, actor_user_id: UUID | None) -> None:
        self._session = session
        self._actor_user_id = actor_user_id

    def add(self, entity: Project) -> Project:
        if self._actor_user_id is not None and entity.created_by_user_id != self._actor_user_id:
            raise ProjectAccessDeniedError("users may only create projects they own")
        if entity.slug is None:
            raise RepositoryError("a persisted project requires a slug")
        record = ProjectRecord(**PROJECT_SPEC.values(entity, include_id=True))
        self._session.add(record)
        self._session.flush()
        return PROJECT_SPEC.contract(record)

    def get(self, project_id: UUID) -> Project:
        query = select(ProjectRecord).where(ProjectRecord.id == project_id)
        if self._actor_user_id is not None:
            query = query.where(_project_access_filter(self._actor_user_id))
        record = self._session.scalar(query)
        if record is None:
            raise EntityNotFoundError(f"project {project_id} was not found")
        return PROJECT_SPEC.contract(record)

    def list(self) -> list[Project]:
        query = select(ProjectRecord).order_by(ProjectRecord.created_at, ProjectRecord.id)
        if self._actor_user_id is not None:
            query = query.where(_project_access_filter(self._actor_user_id))
        return [PROJECT_SPEC.contract(record) for record in self._session.scalars(query)]

    def update(self, entity: Project) -> Project:
        self.get(entity.id)
        record = self._session.get(ProjectRecord, entity.id)
        assert record is not None
        for name in PROJECT_SPEC.update_fields:
            setattr(record, PROJECT_SPEC.record_name(name), getattr(entity, name))
        self._session.flush()
        return PROJECT_SPEC.contract(record)


class _SqlAlchemyScopedRepository(Generic[ContractT, RecordT]):
    def __init__(
        self,
        session: Session,
        context: ProjectContext,
        spec: _RepositorySpec[ContractT, RecordT],
        validator: Callable[[ContractT], None] | None = None,
    ) -> None:
        self._session = session
        self._context = context
        self._spec = spec
        self._validator = validator

    def _validate(self, entity: ContractT) -> None:
        project_id = getattr(entity, "project_id", None)
        if project_id != self._context.project_id:
            raise ProjectBoundaryError("entity does not belong to the repository project")
        if self._validator is not None:
            self._validator(entity)

    def _query(self) -> Any:
        record_type = self._spec.record_type
        return select(record_type).where(record_type.project_id == self._context.project_id)

    def add(self, entity: ContractT) -> ContractT:
        self._validate(entity)
        record = self._spec.record_type(**self._spec.values(entity, include_id=True))
        self._session.add(record)
        self._session.flush()
        return self._spec.contract(record)

    def get(self, entity_id: UUID) -> ContractT:
        record_type = self._spec.record_type
        record = self._session.scalar(self._query().where(record_type.id == entity_id))
        if record is None:
            raise EntityNotFoundError(f"{record_type.__tablename__} {entity_id} was not found")
        return self._spec.contract(record)

    def list(self) -> list[ContractT]:
        record_type = self._spec.record_type
        query = self._query().order_by(record_type.created_at, record_type.id)
        return [self._spec.contract(record) for record in self._session.scalars(query)]

    def update(self, entity: ContractT) -> ContractT:
        self._validate(entity)
        self.get(entity.id)
        record = self._session.get(self._spec.record_type, entity.id)
        assert record is not None
        for name in self._spec.update_fields:
            setattr(record, self._spec.record_name(name), getattr(entity, name))
        self._session.flush()
        return self._spec.contract(record)


class _SqlAlchemyMessageRepository(_SqlAlchemyScopedRepository[Message, MessageRecord]):
    def __init__(self, session: Session, context: ProjectContext) -> None:
        super().__init__(session, context, MESSAGE_SPEC, self._validate_conversation)

    def _validate_conversation(self, entity: Message) -> None:
        conversation_id = self._session.scalar(
            select(ConversationRecord.id).where(
                ConversationRecord.id == entity.conversation_id,
                ConversationRecord.project_id == self._context.project_id,
            )
        )
        if conversation_id is None:
            raise ProjectBoundaryError("message conversation is outside the repository project")

    def _validate(self, entity: Message) -> None:
        self._validate_conversation(entity)

    def _query(self) -> Any:
        return (
            select(MessageRecord)
            .join(ConversationRecord, ConversationRecord.id == MessageRecord.conversation_id)
            .where(ConversationRecord.project_id == self._context.project_id)
        )


class _SqlAlchemyGraphSchemaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: GraphSchemaVersion) -> GraphSchemaVersion:
        record = GraphSchemaVersionRecord(**GRAPH_SCHEMA_SPEC.values(entity, include_id=True))
        self._session.add(record)
        self._session.flush()
        return GRAPH_SCHEMA_SPEC.contract(record)

    def get(self, entity_id: UUID) -> GraphSchemaVersion:
        record = self._session.get(GraphSchemaVersionRecord, entity_id)
        if record is None:
            raise EntityNotFoundError(f"graph schema {entity_id} was not found")
        return GRAPH_SCHEMA_SPEC.contract(record)

    def list(self) -> list[GraphSchemaVersion]:
        query = select(GraphSchemaVersionRecord).order_by(
            GraphSchemaVersionRecord.object_kind,
            GraphSchemaVersionRecord.type_name,
            GraphSchemaVersionRecord.version,
        )
        return [GRAPH_SCHEMA_SPEC.contract(record) for record in self._session.scalars(query)]

    def update(self, entity: GraphSchemaVersion) -> GraphSchemaVersion:
        record = self._session.get(GraphSchemaVersionRecord, entity.id)
        if record is None:
            raise EntityNotFoundError(f"graph schema {entity.id} was not found")
        for name in GRAPH_SCHEMA_SPEC.update_fields:
            setattr(record, name, getattr(entity, name))
        self._session.flush()
        return GRAPH_SCHEMA_SPEC.contract(record)


class SqlAlchemyRepositories:
    """Project-scoped repository set shared by API and worker services."""

    def __init__(self, session: Session, context: ProjectContext) -> None:
        self.session = session
        self.context = context
        self._assert_project_access()
        self.projects = SqlAlchemyProjectRepository(session, context.actor_user_id)
        self.conversations = _SqlAlchemyScopedRepository(session, context, CONVERSATION_SPEC)
        self.messages = _SqlAlchemyMessageRepository(session, context)
        self.tasks = _SqlAlchemyScopedRepository(session, context, TASK_SPEC, self._validate_task)
        self.events = _SqlAlchemyScopedRepository(
            session, context, EVENT_SPEC, self._validate_event
        )
        self.assets = _SqlAlchemyScopedRepository(
            session, context, ASSET_SPEC, self._validate_asset
        )
        self.knowledge_files = _SqlAlchemyScopedRepository(
            session, context, KNOWLEDGE_FILE_SPEC, self._validate_knowledge_file
        )
        self.graph_schemas = _SqlAlchemyGraphSchemaRepository(session)
        self.graph_nodes = _SqlAlchemyScopedRepository(
            session, context, GRAPH_NODE_SPEC, self._validate_node
        )
        self.graph_edges = _SqlAlchemyScopedRepository(
            session, context, GRAPH_EDGE_SPEC, self._validate_edge
        )
        self.graph_chunks = _SqlAlchemyScopedRepository(
            session, context, GRAPH_CHUNK_SPEC, self._validate_chunk
        )
        self.ingestion_runs = _SqlAlchemyScopedRepository(
            session, context, INGESTION_RUN_SPEC, self._validate_ingestion_run
        )

    def _assert_project_access(self) -> None:
        query = select(ProjectRecord.id).where(ProjectRecord.id == self.context.project_id)
        if self.context.actor_user_id is not None:
            query = query.where(_project_access_filter(self.context.actor_user_id))
        if self.session.scalar(query) is None:
            raise ProjectAccessDeniedError(f"actor cannot access project {self.context.project_id}")

    def _validate_knowledge_scope(self, entity: Any) -> None:
        scope_id = self.session.scalar(
            select(KnowledgeScopeRecord.id).where(
                KnowledgeScopeRecord.id == entity.knowledge_scope_id,
                KnowledgeScopeRecord.project_id == self.context.project_id,
            )
        )
        if scope_id is None:
            raise ProjectBoundaryError("knowledge scope is outside the repository project")

    def _validate_reference(
        self, record_type: type[Any], entity_id: UUID | None, label: str
    ) -> None:
        if entity_id is None:
            return
        matching_id = self.session.scalar(
            select(record_type.id).where(
                record_type.id == entity_id,
                record_type.project_id == self.context.project_id,
            )
        )
        if matching_id is None:
            raise ProjectBoundaryError(f"{label} is outside the repository project")

    def _validate_task(self, entity: AgentTask) -> None:
        self._validate_reference(ConversationRecord, entity.conversation_id, "task conversation")

    def _validate_event(self, entity: ProductEvent) -> None:
        if entity.research_run_id is not None:
            raise RepositoryError("research-run events are not persisted in the V1 schema yet")
        self._validate_reference(AgentTaskRecord, entity.agent_task_id, "event task")
        self._validate_reference(ConversationRecord, entity.conversation_id, "event conversation")

    def _validate_asset(self, entity: Asset) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(ConversationRecord, entity.conversation_id, "asset conversation")
        self._validate_reference(AgentTaskRecord, entity.agent_task_id, "asset task")

    def _validate_knowledge_file(self, entity: KnowledgeFile) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(
            ConversationRecord, entity.conversation_id, "knowledge file conversation"
        )
        self._validate_reference(AssetRecord, entity.asset_id, "knowledge file asset")

    def _validate_node(self, entity: GraphNode) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(AssetRecord, entity.asset_id, "graph node asset")
        self._validate_reference(
            KnowledgeFileRecord, entity.knowledge_file_id, "graph node knowledge file"
        )

    def _validate_edge(self, entity: GraphEdge) -> None:
        self._validate_knowledge_scope(entity)
        node_ids = set(
            self.session.scalars(
                select(GraphNodeRecord.id).where(
                    GraphNodeRecord.project_id == self.context.project_id,
                    GraphNodeRecord.id.in_([entity.from_node_id, entity.to_node_id]),
                )
            )
        )
        if node_ids != {entity.from_node_id, entity.to_node_id}:
            raise ProjectBoundaryError("graph edge nodes are outside the repository project")

    def _validate_chunk(self, entity: GraphChunk) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(GraphNodeRecord, entity.node_id, "graph chunk node")
        self._validate_reference(AssetRecord, entity.asset_id, "graph chunk asset")
        self._validate_reference(
            KnowledgeFileRecord, entity.knowledge_file_id, "graph chunk knowledge file"
        )

    def _validate_ingestion_run(self, entity: IngestionRun) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(AgentTaskRecord, entity.agent_task_id, "ingestion task")
        self._validate_reference(AssetRecord, entity.asset_id, "ingestion asset")
        self._validate_reference(GraphNodeRecord, entity.target_node_id, "ingestion target node")


@dataclass
class InMemoryRepositoryStore:
    projects: dict[UUID, Project] = field(default_factory=dict)
    memberships: set[tuple[UUID, UUID]] = field(default_factory=set)
    knowledge_scopes: dict[UUID, UUID] = field(default_factory=dict)
    entities: dict[type[BaseModel], dict[UUID, BaseModel]] = field(default_factory=dict)

    def grant_project_access(self, project_id: UUID, user_id: UUID) -> None:
        self.memberships.add((project_id, user_id))

    def register_knowledge_scope(self, scope_id: UUID, project_id: UUID) -> None:
        self.knowledge_scopes[scope_id] = project_id


class InMemoryProjectRepository:
    def __init__(self, store: InMemoryRepositoryStore, actor_user_id: UUID | None) -> None:
        self._store = store
        self._actor_user_id = actor_user_id

    def _can_access(self, project: Project) -> bool:
        return (
            self._actor_user_id is None
            or project.created_by_user_id == self._actor_user_id
            or (project.id, self._actor_user_id) in self._store.memberships
        )

    def add(self, entity: Project) -> Project:
        if self._actor_user_id is not None and entity.created_by_user_id != self._actor_user_id:
            raise ProjectAccessDeniedError("users may only create projects they own")
        if entity.slug is None:
            raise RepositoryError("a persisted project requires a slug")
        self._store.projects[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)

    def get(self, project_id: UUID) -> Project:
        project = self._store.projects.get(project_id)
        if project is None or not self._can_access(project):
            raise EntityNotFoundError(f"project {project_id} was not found")
        return project.model_copy(deep=True)

    def list(self) -> list[Project]:
        projects = [
            project for project in self._store.projects.values() if self._can_access(project)
        ]
        return [
            project.model_copy(deep=True)
            for project in sorted(projects, key=lambda p: (p.created_at, p.id))
        ]

    def update(self, entity: Project) -> Project:
        self.get(entity.id)
        self._store.projects[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)


class _InMemoryScopedRepository(Generic[ContractT]):
    def __init__(
        self,
        store: InMemoryRepositoryStore,
        context: ProjectContext,
        contract_type: type[ContractT],
        validator: Callable[[ContractT], None] | None = None,
    ) -> None:
        self._store = store
        self._context = context
        self._contract_type = contract_type
        self._validator = validator

    @property
    def _entities(self) -> dict[UUID, ContractT]:
        return self._store.entities.setdefault(self._contract_type, {})  # type: ignore[return-value]

    def _validate(self, entity: ContractT) -> None:
        if getattr(entity, "project_id", None) != self._context.project_id:
            raise ProjectBoundaryError("entity does not belong to the repository project")
        if self._validator is not None:
            self._validator(entity)

    def add(self, entity: ContractT) -> ContractT:
        self._validate(entity)
        self._entities[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)

    def get(self, entity_id: UUID) -> ContractT:
        entity = self._entities.get(entity_id)
        if entity is None or getattr(entity, "project_id", None) != self._context.project_id:
            raise EntityNotFoundError(f"{self._contract_type.__name__} {entity_id} was not found")
        return entity.model_copy(deep=True)

    def list(self) -> list[ContractT]:
        entities = [
            entity
            for entity in self._entities.values()
            if getattr(entity, "project_id", None) == self._context.project_id
        ]
        return [
            entity.model_copy(deep=True)
            for entity in sorted(entities, key=lambda e: (e.created_at, e.id))
        ]

    def update(self, entity: ContractT) -> ContractT:
        self._validate(entity)
        self.get(entity.id)
        self._entities[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)


class _InMemoryMessageRepository(_InMemoryScopedRepository[Message]):
    def _validate(self, entity: Message) -> None:
        conversations = self._store.entities.get(Conversation, {})
        conversation = conversations.get(entity.conversation_id)
        if conversation is None or conversation.project_id != self._context.project_id:
            raise ProjectBoundaryError("message conversation is outside the repository project")

    def get(self, entity_id: UUID) -> Message:
        entity = self._entities.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Message {entity_id} was not found")
        self._validate(entity)
        return entity.model_copy(deep=True)

    def list(self) -> list[Message]:
        entities = []
        for entity in self._entities.values():
            try:
                self._validate(entity)
            except ProjectBoundaryError:
                continue
            entities.append(entity)
        return [entity.model_copy(deep=True) for entity in sorted(entities, key=lambda e: e.id)]


class _InMemoryGraphSchemaRepository(_InMemoryScopedRepository[GraphSchemaVersion]):
    def _validate(self, entity: GraphSchemaVersion) -> None:
        return None

    def get(self, entity_id: UUID) -> GraphSchemaVersion:
        entity = self._entities.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"GraphSchemaVersion {entity_id} was not found")
        return entity.model_copy(deep=True)

    def list(self) -> list[GraphSchemaVersion]:
        return [
            entity.model_copy(deep=True)
            for entity in sorted(
                self._entities.values(),
                key=lambda schema: (schema.object_kind, schema.type_name, schema.version),
            )
        ]


class InMemoryRepositories:
    """In-memory repository set with the same project-boundary behavior as PostgreSQL."""

    def __init__(self, store: InMemoryRepositoryStore, context: ProjectContext) -> None:
        self.store = store
        self.context = context
        project = store.projects.get(context.project_id)
        can_access = project is not None and (
            context.actor_user_id is None
            or project.created_by_user_id == context.actor_user_id
            or (context.project_id, context.actor_user_id) in store.memberships
        )
        if not can_access:
            raise ProjectAccessDeniedError(f"actor cannot access project {context.project_id}")

        self.projects = InMemoryProjectRepository(store, context.actor_user_id)
        self.conversations = _InMemoryScopedRepository(store, context, Conversation)
        self.messages = _InMemoryMessageRepository(store, context, Message)
        self.tasks = _InMemoryScopedRepository(store, context, AgentTask, self._validate_task)
        self.events = _InMemoryScopedRepository(store, context, ProductEvent, self._validate_event)
        self.assets = _InMemoryScopedRepository(store, context, Asset, self._validate_asset)
        self.knowledge_files = _InMemoryScopedRepository(
            store, context, KnowledgeFile, self._validate_knowledge_file
        )
        self.graph_schemas = _InMemoryGraphSchemaRepository(store, context, GraphSchemaVersion)
        self.graph_nodes = _InMemoryScopedRepository(store, context, GraphNode, self._validate_node)
        self.graph_edges = _InMemoryScopedRepository(store, context, GraphEdge, self._validate_edge)
        self.graph_chunks = _InMemoryScopedRepository(
            store, context, GraphChunk, self._validate_chunk
        )
        self.ingestion_runs = _InMemoryScopedRepository(
            store, context, IngestionRun, self._validate_ingestion_run
        )

    def _validate_knowledge_scope(self, entity: Any) -> None:
        if self.store.knowledge_scopes.get(entity.knowledge_scope_id) != self.context.project_id:
            raise ProjectBoundaryError("knowledge scope is outside the repository project")

    def _validate_reference(
        self, contract_type: type[BaseModel], entity_id: UUID | None, label: str
    ) -> None:
        if entity_id is None:
            return
        entity = self.store.entities.get(contract_type, {}).get(entity_id)
        if entity is None or getattr(entity, "project_id", None) != self.context.project_id:
            raise ProjectBoundaryError(f"{label} is outside the repository project")

    def _validate_task(self, entity: AgentTask) -> None:
        self._validate_reference(Conversation, entity.conversation_id, "task conversation")

    def _validate_event(self, entity: ProductEvent) -> None:
        if entity.research_run_id is not None:
            raise RepositoryError("research-run events are not persisted in the V1 schema yet")
        self._validate_reference(AgentTask, entity.agent_task_id, "event task")
        self._validate_reference(Conversation, entity.conversation_id, "event conversation")

    def _validate_asset(self, entity: Asset) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(Conversation, entity.conversation_id, "asset conversation")
        self._validate_reference(AgentTask, entity.agent_task_id, "asset task")

    def _validate_knowledge_file(self, entity: KnowledgeFile) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(
            Conversation, entity.conversation_id, "knowledge file conversation"
        )
        self._validate_reference(Asset, entity.asset_id, "knowledge file asset")

    def _validate_node(self, entity: GraphNode) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(Asset, entity.asset_id, "graph node asset")
        self._validate_reference(
            KnowledgeFile, entity.knowledge_file_id, "graph node knowledge file"
        )

    def _validate_edge(self, entity: GraphEdge) -> None:
        self._validate_knowledge_scope(entity)
        nodes = self.store.entities.get(GraphNode, {})
        for node_id in (entity.from_node_id, entity.to_node_id):
            node = nodes.get(node_id)
            if node is None or node.project_id != self.context.project_id:
                raise ProjectBoundaryError("graph edge nodes are outside the repository project")

    def _validate_chunk(self, entity: GraphChunk) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(GraphNode, entity.node_id, "graph chunk node")
        self._validate_reference(Asset, entity.asset_id, "graph chunk asset")
        self._validate_reference(
            KnowledgeFile, entity.knowledge_file_id, "graph chunk knowledge file"
        )

    def _validate_ingestion_run(self, entity: IngestionRun) -> None:
        self._validate_knowledge_scope(entity)
        self._validate_reference(AgentTask, entity.agent_task_id, "ingestion task")
        self._validate_reference(Asset, entity.asset_id, "ingestion asset")
        self._validate_reference(GraphNode, entity.target_node_id, "ingestion target node")
