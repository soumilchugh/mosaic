# Architecture

## Components

```text
apps/web                  Knowledge workspace UI
services/api              Durable REST commands and WebSocket stream
services/worker           Agent execution, ingestion, memory, and application jobs
packages/harness_core     DeepAgents adapter, event mapping, tool bridges
packages/knowledge_core   Assets, knowledge files, graph, memory, connectors
packages/research_core    Deep research/report applications built on knowledge_core
```

The frontend workspace is knowledge-first: a left chat/control panel, central
knowledge/report/application surface, and right evidence/assets/graph/memory/activity
panel. Report generation is one application inside this workspace. See
[frontend-workspace.md](frontend-workspace.md) for the editor and visual asset design.

## Local Services

```text
web        Next.js frontend
api        FastAPI backend
worker     Background agent, ingestion, memory, research, and report worker
postgres   Product state, pgvector projections, pgmq queue, evidence graph
minio      Local ObjectStore-compatible storage
```

Production V1 uses Supabase Cloud for Postgres, Auth, Storage, Realtime, and Queues. The
FastAPI API and long-running Python workers remain ordinary containers. See
[deployment-strategy.md](deployment-strategy.md). Neo4j and Redis are optional later
services, introduced only for measured graph, cache, coordination, or pub/sub needs.

## Configuration And Providers

The API and worker load the same typed `MosaicSettings` environment contract. Provider
selection is explicit for the database, model, search, storage, queue, and sandbox. A
small shared registry lazily constructs the configured implementation, allowing local,
Supabase, and future AWS adapters to implement the same service boundary.

All Mosaic settings use the `MOSAIC_` prefix. Credentials and database URLs are secret
types and must not be included in logs; startup diagnostics use the allowlisted
`safe_summary()` fields. Local defaults use fake/no-op model and search providers,
filesystem storage, an in-memory queue, and a local sandbox so development does not
require cloud credentials.

## Persistence Model

Postgres is the product system of record. Object storage stores file bytes. DeepAgents
uses durable thread/checkpoint persistence keyed by product conversations and agent
tasks.

```text
User
  -> GlobalKnowledgeScope
  -> Project
    -> ProjectKnowledgeScope
    -> Conversation
      -> Message
      -> AgentTask
        -> ProductEvent
        -> InterventionRequest
        -> DeepAgentsThread
    -> Asset
    -> KnowledgeFile
    -> GraphNode / GraphEdge
    -> MemoryRecord / MemoryLink
    -> SourceConnector
```

Core Postgres tables should include:

```text
users
organizations
projects
project_memberships
knowledge_scopes
conversations
messages
agent_tasks
research_runs
product_events
intervention_requests
deepagents_threads
memory_records
memory_links
source_connectors
source_sync_runs
assets
knowledge_files
graph_nodes
graph_edges
graph_chunks
graph_schema_versions
graph_candidates
graph_candidate_evidence
graph_entity_aliases
graph_entity_merges
graph_embeddings
graph_retrieval_runs
ingestion_runs
```

See [data-model.md](data-model.md) for the ERD, table responsibilities, and initial
field-level schema. See [knowledge-graph-design.md](knowledge-graph-design.md) for the
evidence-first graph lifecycle and retrieval policy.

Object storage, MinIO locally and Supabase Storage in V1 production, owns:

- uploaded files
- fetched source snapshots
- connector snapshots such as Slack threads, GitHub files, or Drive documents
- generated report artifacts
- charts, images, slide drafts, exports
- code archives or repository snapshots when needed

Postgres stores object metadata and storage URIs, not large file bytes.

### Repository Boundary

`knowledge_core.persistence` exposes the shared repository interface used by the API and
worker. Product code passes Pydantic contracts to repositories and does not depend on
SQLAlchemy records or write ad hoc queries.

API requests create a `ProjectContext` with both the authenticated user and project.
Repository construction verifies ownership or project membership, then every operation
enforces the same project and knowledge-scope boundary on the record and its references.
Trusted background workers use `ProjectContext.for_worker(project_id)` after receiving a
validated project-scoped task.

The SQLAlchemy repository set participates in the caller's database session; the API or
worker transaction owns commit and rollback. The matching in-memory repository set is
used for deterministic unit tests and applies the same access and cross-project rules.

## Context Assembly

Every new user turn should build a bounded context pack before starting or resuming
DeepAgents:

```text
conversation summary
recent messages
active agent task or application state
pending interventions
relevant memory records
project research map
project knowledge scope results
user/org global knowledge scope results
graph retrieval result sets
selected source/code cards
asset metadata
DeepAgents thread/checkpoint ID
```

The context pack should be reproducible from persisted state. DeepAgents can maintain its
own checkpoint state, but the product must persist the user-visible projection: messages,
events, interventions, assets, knowledge updates, and memory updates.

Context assembly should treat source knowledge and interaction memory separately:

- source knowledge answers "what do the documents, connectors, code, and web sources
  say?"
- interaction memory answers "what has the user taught or decided with the agent?"

Both can be linked through graph records and memory links.

## Evidence-First Graph

The graph records source-relative assertions, not a single undifferentiated truth store.
Parsers and models write extraction candidates first. Candidates are promoted only after
typed validation, permission checks, source-range resolution, and entity resolution.

```text
asset -> structured chunk -> extraction candidate -> validation
      -> canonical claim/edge -> retrieval projection -> cited answer/report
```

Every canonical semantic relationship keeps a path to the exact source revision and
range that supports or contradicts it. Conflicting claims remain separate and can be
corrected or superseded without deleting their history.

Postgres owns canonical identities and records. Full-text, vector, and optional Neo4j
indexes are rebuildable projections keyed by those identities. The query planner chooses
lexical, vector, entity, graph, or hybrid retrieval based on the query class; graph
traversal is not mandatory for ordinary fact lookup.

## API Shape

```text
POST /projects
GET  /projects/{project_id}
GET  /knowledge-scopes/{knowledge_scope_id}
POST /conversations
GET  /conversations/{conversation_id}
POST /conversations/{conversation_id}/messages
POST /assets
POST /ingestion-runs
POST /source-connectors
GET  /source-connectors/{connector_id}
POST /agent-tasks
GET  /agent-tasks/{task_id}
GET  /memories
POST /memories
POST /research-runs
GET  /research-runs/{run_id}
GET  /research-runs/{run_id}/report
POST /research-runs/{run_id}/cancel
POST /research-runs/{run_id}/interventions
WS   /research-runs/{run_id}/stream
```

## Event Stream

The worker runs DeepAgents through `packages/harness_core`. DeepAgents-native stream
events are mapped into product events that the API can persist and forward over
WebSocket. Product events include:

- `run.started`
- `agent.answer_started`
- `agent.answer_delta`
- `ingestion.started`
- `ingestion.completed`
- `graph.candidate_created`
- `graph.candidate_promoted`
- `graph.candidate_rejected`
- `graph.entity_merge_proposed`
- `graph.projection_updated`
- `retrieval.completed`
- `connector.sync_started`
- `connector.sync_completed`
- `memory.candidate_created`
- `memory.saved`
- `memory.updated`
- `planner.topic_proposed`
- `planner.outline_updated`
- `user_intervention.requested`
- `research.query_started`
- `source.found`
- `source.processed`
- `source.deepened`
- `code.reference_added`
- `claim.extracted`
- `section.started`
- `report.delta`
- `citation.added`
- `citation.stale`
- `editor.suggestion`
- `artifact.generated`
- `run.completed`
- `run.failed`

## Harness Boundary

DeepAgents is the V1 agent engine. The product should not call DeepAgents directly from
every service. Instead, `packages/harness_core` exposes a small adapter boundary:

```text
AgentTask -> DeepAgents run -> ProductEvent stream
```

This keeps the API, worker, and frontend coupled to our product contracts rather than to
DeepAgents internals.

## Source Connectors

Connectors are source adapters that bring external knowledge into the same asset,
knowledge file, graph, and memory substrate as local uploads.

See [source-connectors.md](source-connectors.md) for connector families, standard output,
ingestion levels, permissions, and recommended build order.

V1 connector contract:

```text
ConnectorAccount
  -> SourceConnector
  -> SourceSyncRun
  -> Asset / KnowledgeFile / GraphNode / GraphChunk
```

Initial connector candidates:

- local uploads
- web URLs and crawled sites
- Slack channels, threads, files, decisions, and action items
- GitHub repositories, issues, pull requests, commits, and code files
- Google Drive or Notion documents
- Linear/Jira work items
- email and calendar sources later
- databases and internal APIs later

Each connector sync should preserve source IDs, timestamps, authors, permissions,
checksums, and enough provenance for citations or audit.

## Memory Layer

The memory layer stores durable lessons from human-agent collaboration. It is separate
from raw conversation history.

Memory candidates can come from:

- user corrections
- stable user preferences
- project decisions
- terminology definitions
- source quality judgments
- reusable conclusions produced during chat or research
- explicit "remember this" instructions

Memory records should have scope:

- user-global
- project-local
- organization-global later

Memory links connect memories to messages, assets, knowledge files, graph nodes, chunks,
reports, or connector records. This lets the agent recall both the lesson and the source
or conversation that created it.
