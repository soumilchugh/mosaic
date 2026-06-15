# Architecture

## Components

```text
apps/web                  Research workspace UI
services/api              Durable REST commands and WebSocket stream
services/worker           Agent execution and research jobs
packages/harness_core     DeepAgents adapter, event mapping, tool bridges
packages/research_core    Deep research roles, graph schema, prompts, workflows
```

## Local Services

```text
web        Next.js frontend
api        FastAPI backend
worker     Background research worker
postgres   Users, workspaces, conversations, runs, events, graph, metadata
redis      Queue, pub/sub, transient state
neo4j      Source and report graphs
minio      Local object storage
```

Neo4j should be optional at first. V1 can use Postgres as the graph repository for nodes,
edges, chunks, ingestion state, and file/source/code references, then project to Neo4j
later if multi-hop graph queries become central.

## Persistence Model

Postgres is the product system of record. Object storage stores file bytes. DeepAgents
uses durable thread/checkpoint persistence keyed by product conversations and research
runs.

```text
User
  -> Workspace
    -> Conversation
      -> Message
      -> ResearchRun
        -> ResearchEvent
        -> InterventionRequest
        -> DeepAgentsThread
    -> Asset
    -> KnowledgeFile
    -> GraphNode / GraphEdge
```

Core Postgres tables should include:

```text
users
workspaces
workspace_memberships
conversations
messages
research_runs
research_events
intervention_requests
deepagents_threads
assets
knowledge_files
graph_nodes
graph_edges
graph_chunks
ingestion_runs
```

See [data-model.md](data-model.md) for the ERD, table responsibilities, and initial
field-level schema.

Object storage, MinIO locally and S3 in production, owns:

- uploaded files
- fetched source snapshots
- generated report artifacts
- charts, images, slide drafts, exports
- code archives or repository snapshots when needed

Postgres stores object metadata and storage URIs, not large file bytes.

## Context Assembly

Every new user turn should build a bounded context pack before starting or resuming
DeepAgents:

```text
conversation summary
recent messages
active research run state
pending interventions
workspace research map
graph retrieval result sets
selected source/code cards
asset metadata
DeepAgents thread/checkpoint ID
```

The context pack should be reproducible from persisted state. DeepAgents can maintain its
own checkpoint state, but the product must persist the user-visible projection: messages,
events, interventions, assets, and knowledge graph updates.

## API Shape

```text
POST /workspaces
GET  /workspaces/{workspace_id}
POST /conversations
GET  /conversations/{conversation_id}
POST /conversations/{conversation_id}/messages
POST /assets
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
- `editor.suggestion`
- `artifact.generated`
- `run.completed`
- `run.failed`

## Harness Boundary

DeepAgents is the V1 agent engine. The product should not call DeepAgents directly from
every service. Instead, `packages/harness_core` exposes a small adapter boundary:

```text
ResearchTask -> DeepAgents run -> ResearchEvent stream
```

This keeps the API, worker, and frontend coupled to our product contracts rather than to
DeepAgents internals.
