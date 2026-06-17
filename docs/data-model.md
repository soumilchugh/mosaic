# Data Model And ERD

## Purpose

The data model separates durable product state from agent execution state and file bytes.

- Postgres is the product system of record.
- Object storage owns uploaded, fetched, and generated file bytes.
- DeepAgents/LangGraph owns checkpoint internals, keyed by product IDs.
- The file-native graph starts in Postgres and can later project to Neo4j.

## High-Level ERD

```mermaid
erDiagram
    users ||--o{ project_memberships : belongs_to
    users ||--o{ knowledge_scopes : owns_global
    organizations ||--o{ knowledge_scopes : owns_global
    projects ||--o{ project_memberships : has
    projects ||--o{ conversations : owns
    projects ||--o{ knowledge_scopes : owns_local
    knowledge_scopes ||--o{ assets : owns
    knowledge_scopes ||--o{ knowledge_files : owns
    knowledge_scopes ||--o{ graph_nodes : owns
    conversations ||--o{ messages : has
    conversations ||--o{ research_runs : starts
    conversations ||--o{ deepagents_threads : maps_to
    research_runs ||--o{ research_events : emits
    research_runs ||--o{ intervention_requests : pauses_for
    research_runs ||--o{ deepagents_threads : maps_to
    research_runs ||--o{ ingestion_runs : performs
    assets ||--o{ knowledge_files : materializes
    assets ||--o{ graph_nodes : referenced_by
    knowledge_files ||--o{ graph_nodes : describes
    graph_nodes ||--o{ graph_edges : from_node
    graph_nodes ||--o{ graph_edges : to_node
    graph_nodes ||--o{ graph_chunks : contains
    graph_nodes ||--o{ ingestion_runs : target
```

## Identity, Project, And Knowledge Scope Tables

### `users`

Represents an account that can own or participate in projects and global knowledge
scopes.

Important fields:

```text
id uuid primary key
email text unique not null
display_name text
created_at timestamptz
updated_at timestamptz
```

Notes:

- V1 can keep auth simple, but every durable object should be traceable to a user.
- External auth provider IDs can be added later.

### `organizations`

Optional team boundary. V1 can defer multi-user org features, but the model should not
block organization-level knowledge later.

Important fields:

```text
id uuid primary key
name text not null
slug text unique
created_by_user_id uuid references users(id)
created_at timestamptz
updated_at timestamptz
archived_at timestamptz null
```

### `projects`

A project is the top-level work container for conversations and project-specific
knowledge. This is what earlier docs called a workspace.

Important fields:

```text
id uuid primary key
organization_id uuid references organizations(id) null
name text not null
slug text
created_by_user_id uuid references users(id)
default_knowledge_scope_id uuid references knowledge_scopes(id) null
status text -- active, archived
metadata jsonb
created_at timestamptz
updated_at timestamptz
archived_at timestamptz null
```

Notes:

- A user can have many projects.
- Each project has a local knowledge scope.
- Retrieval can also include user-global or organization-global knowledge scopes.

### `project_memberships`

Connects users to projects.

Important fields:

```text
project_id uuid references projects(id)
user_id uuid references users(id)
role text -- owner, editor, viewer
created_at timestamptz
primary key (project_id, user_id)
```

### `knowledge_scopes`

A knowledge scope owns reusable assets, knowledge files, and graph records. Scopes let
the system distinguish user-global knowledge from project-local knowledge.

Important fields:

```text
id uuid primary key
scope_type text -- user_global, organization_global, project
owner_user_id uuid references users(id) null
owner_organization_id uuid references organizations(id) null
project_id uuid references projects(id) null
name text not null
description text
visibility text -- private, project, organization
created_at timestamptz
updated_at timestamptz
```

Retrieval order:

```text
1. current conversation/run state
2. current project knowledge scope
3. user global knowledge scope
4. organization global knowledge scope, if enabled
5. external sources/connectors
```

This supports reusable knowledge without mixing project-specific evidence into every
answer.

## Conversation And Session Tables

### `conversations`

A conversation is the user-visible session. It can have many messages and many research
runs.

Important fields:

```text
id uuid primary key
project_id uuid references projects(id)
created_by_user_id uuid references users(id)
title text
status text -- active, archived
summary text
metadata jsonb
created_at timestamptz
updated_at timestamptz
```

Notes:

- `summary` is the compact conversation memory used during context assembly.
- The raw message log remains in `messages`.

### `messages`

Stores user, assistant, and system-visible messages.

Important fields:

```text
id uuid primary key
conversation_id uuid references conversations(id)
role text -- user, assistant, system, tool
content text
content_format text -- markdown, plain_text, json
user_id uuid references users(id) null
research_run_id uuid references research_runs(id) null
metadata jsonb
created_at timestamptz
```

Notes:

- Assistant final answers and user turns should be persisted here.
- Tool internals belong in events/traces, not necessarily as user-visible messages.

### `deepagents_threads`

Maps product sessions/runs to DeepAgents/LangGraph thread IDs and checkpoint namespaces.

Important fields:

```text
id uuid primary key
project_id uuid references projects(id)
conversation_id uuid references conversations(id) null
research_run_id uuid references research_runs(id) null
thread_id text not null
checkpoint_namespace text
status text -- active, paused, completed, failed
metadata jsonb
created_at timestamptz
updated_at timestamptz
unique(thread_id)
```

Thread strategy:

- Conversation-level thread: preserves long-lived conversational state.
- Research-run-level thread: isolates expensive deep research execution.
- V1 should support both by allowing either `conversation_id` or `research_run_id`.

## Research Run Tables

### `research_runs`

Represents a durable unit of deep research work.

Important fields:

```text
id uuid primary key
project_id uuid references projects(id)
conversation_id uuid references conversations(id)
created_by_user_id uuid references users(id)
intent text not null
status text -- created, planning, awaiting_intervention, researching, writing, editing, completed, failed, cancelled
depth text -- quick, standard, deep
strategy text -- breadth_first, depth_first, hybrid
output_format text -- markdown, report, deck_later
settings jsonb
started_at timestamptz null
completed_at timestamptz null
created_at timestamptz
updated_at timestamptz
```

Notes:

- `research_runs` is the parent for events, interventions, ingestion work, and generated
  report artifacts.

### `research_events`

Append-only product event timeline. This is what the frontend can replay after reconnect.

Important fields:

```text
id uuid primary key
project_id uuid references projects(id)
conversation_id uuid references conversations(id)
research_run_id uuid references research_runs(id)
sequence bigint not null
type text not null
payload jsonb not null
deepagents_event_id text null
trace_id text null
created_at timestamptz
unique(research_run_id, sequence)
```

Notes:

- Product events are stable contracts.
- DeepAgents-native details can be attached in metadata, but the frontend should consume
  product event types.

### `intervention_requests`

Stores human-in-the-loop approval/edit/reject states.

Important fields:

```text
id uuid primary key
project_id uuid references projects(id)
conversation_id uuid references conversations(id)
research_run_id uuid references research_runs(id)
deepagents_thread_id uuid references deepagents_threads(id)
type text -- topic_approval, tool_approval, memory_write, filesystem_write, export_approval
status text -- pending, approved, edited, rejected, expired, resolved
request_payload jsonb
response_payload jsonb null
requested_at timestamptz
responded_at timestamptz null
expires_at timestamptz null
```

## Asset And File Tables

### `assets`

Metadata for file bytes stored in object storage.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
conversation_id uuid references conversations(id) null
research_run_id uuid references research_runs(id) null
created_by_user_id uuid references users(id) null
kind text -- upload, fetched_source, generated_report, chart, image, code_snapshot, export
filename text
mime_type text
size_bytes bigint
checksum text
storage_uri text not null
source_url text null
source_metadata jsonb
status text -- available, processing, failed, deleted
created_at timestamptz
updated_at timestamptz
```

Notes:

- Object storage is MinIO locally and S3 in production.
- Postgres stores pointers and provenance, not large bytes.

### `knowledge_files`

Agent-readable markdown or text files in the virtual workspace.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
conversation_id uuid references conversations(id) null
research_run_id uuid references research_runs(id) null
asset_id uuid references assets(id) null
path text not null
file_type text -- research_map, topic_card, source_card, repo_card, report_section, scratch
title text
frontmatter jsonb
content_hash text
status text -- active, stale, archived
created_by text -- user, agent, system
created_at timestamptz
updated_at timestamptz
unique(knowledge_scope_id, path)
```

Notes:

- These are the files the agent can read and update.
- They are also graph entry points through `graph_nodes.file_path`.
- `knowledge_scope_id` controls whether a file is global, organization-level, or
  project-local.

## How The Graph References Files

The graph should distinguish original file bytes from agent-readable knowledge files.

Use `asset_id` when a graph record points to original or generated file bytes in object
storage:

```text
uploaded PDF
uploaded image
fetched web snapshot
code archive
generated chart
exported slide deck
```

Use `knowledge_file_id` when a graph record points to a markdown/text file in the virtual
workspace:

```text
source_017.md
topic_supply_chain.md
repo_card.md
research_map.md
report_section_01.md
image_004.md
```

A graph node can point to both when both representations exist:

```text
GraphNode(type = source)
  asset_id = original PDF in object storage
  knowledge_file_id = source card markdown file
```

Use `graph_chunks` when the graph needs to reference a specific page range, section, byte
range, or code line range inside an asset or knowledge file.

Example:

```text
Source017
  -> asset_id: asset_pdf_123
  -> knowledge_file_id: kf_source_017_md
  -> HAS_CHUNK: graph_chunk pages 59-80
```

This lets graph-guided retrieval return:

- the source/card file the agent should read first
- the raw asset to inspect if deeper evidence is needed
- the exact page/section/line range already known by the graph

## Graph Tables

### `graph_nodes`

Generic node table for the file-native knowledge graph.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
type text -- topic, source, document, repository, commit, code_file, symbol, chunk, entity, claim, fact, report_section, artifact
external_id text null
title text
summary text
knowledge_file_id uuid references knowledge_files(id) null
asset_id uuid references assets(id) null
metadata jsonb
ingestion_level text null
created_at timestamptz
updated_at timestamptz
```

Notes:

- `external_id` can store source IDs, repository IDs, commit SHAs, provider IDs, etc.
- Nodes are mechanical records; relevance is judged by the agent.

### `graph_edges`

Directed relationship table.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
from_node_id uuid references graph_nodes(id)
relation text -- COVERS, DESCRIBED_BY, HAS_CHUNK, SUPPORTS, CONTRADICTS, CITES, DEFINES, DEPENDS_ON, DERIVED_FROM
to_node_id uuid references graph_nodes(id)
confidence numeric null
metadata jsonb
created_at timestamptz
updated_at timestamptz
```

Notes:

- This table lets Postgres act as the V1 graph repository.
- Neo4j can later mirror these records as a projection.

### `graph_chunks`

Chunk/page/range metadata for source and code references.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
node_id uuid references graph_nodes(id)
knowledge_file_id uuid references knowledge_files(id) null
asset_id uuid references assets(id) null
chunk_index integer
source_range text -- page range, byte range, line range, section heading
text_preview text
content_hash text
metadata jsonb
created_at timestamptz
updated_at timestamptz
```

Notes:

- Store enough preview to route the agent.
- Full text can live in knowledge files/object storage; database can add full-text search
  later.

### `ingestion_runs`

Tracks progressive ingestion and targeted deepening.

Important fields:

```text
id uuid primary key
knowledge_scope_id uuid references knowledge_scopes(id)
project_id uuid references projects(id) null
research_run_id uuid references research_runs(id) null
target_node_id uuid references graph_nodes(id)
mode text -- shallow_card, section_indexed, topic_deepened, claims_and_citations, code_symbol_trace
status text -- queued, running, completed, failed, cancelled
coverage jsonb -- pages, sections, files, symbols, topics
budget jsonb
result_summary text
error text null
started_at timestamptz null
completed_at timestamptz null
created_at timestamptz
```

## Reports And Citations

Report sections can be represented as `knowledge_files` and `graph_nodes` initially.
Dedicated report tables can be added when editing/export workflows need stronger
constraints.

V1 recommendation:

```text
knowledge_files(file_type = report_section)
graph_nodes(type = report_section)
graph_edges(report_section)-[:CITES]->(source/chunk/code_reference)
```

This keeps report state aligned with the same file-native graph model.

## Context Pack Inputs

A context pack is assembled from these records:

```text
conversation summary         conversations.summary
recent messages              messages
active run state             research_runs
pending interventions        intervention_requests
thread/checkpoint mapping    deepagents_threads
graph result sets            graph_nodes, graph_edges, graph_chunks
selected knowledge files     knowledge_files
asset metadata               assets
event history                research_events
```

The context pack should record which database IDs were included so a run is auditable and
reproducible.

## Indexing Strategy

Initial indexes:

```text
project_id on project-scoped runtime tables
knowledge_scope_id on assets, knowledge_files, graph_nodes, graph_edges, graph_chunks
conversation_id on messages, research_runs, research_events
research_run_id on events, interventions, ingestion_runs
unique(research_run_id, sequence) for event replay
unique(knowledge_scope_id, path) for knowledge_files
from_node_id, to_node_id, relation on graph_edges
type, external_id on graph_nodes
asset checksum for dedupe
```

Later indexes:

- Postgres full-text over `knowledge_files` and `graph_chunks`
- optional vector search over summaries/chunks
- Neo4j projection for complex multi-hop graph queries
- code symbol/path indexes for repository research

## Open Decisions

- Should V1 use one DeepAgents thread per conversation plus child threads for research
  runs, or only run-level threads?
- Should the UI call the top-level container "project" everywhere, or keep "workspace" as
  the product label while using `projects` internally?
- Should user-global knowledge be enabled in V1 or reserved until project-local retrieval
  is stable?
- Should report sections get dedicated tables immediately or stay as graph-backed
  knowledge files?
- Should graph chunks store full text in Postgres or only previews plus file/object
  references?
- Which ORM/migration stack should we use: SQLAlchemy + Alembic, SQLModel + Alembic, or
  plain SQL migrations?
