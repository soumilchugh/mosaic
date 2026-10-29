# Agent Harness

Private working repository for an agentic multimodal knowledge and memory platform.

The goal is to turn local files, connected data sources, conversations, and agent work
into a living, evidence-backed knowledge base. Users should be able to ask questions,
inspect sources, teach the agent through corrections and decisions, deepen existing
knowledge, perform research, and generate reports from the same underlying system.

Deep research and report generation are applications built on the platform, not the
entire product.

## Product Model

The platform has four layers:

1. **Sources and assets**: PDFs, documents, images, spreadsheets, code, web pages, and
   connectors such as GitHub, Slack, Notion, and Google Drive.
2. **Knowledge base**: source cards, structured chunks, entities, topics, claims,
   relationships, citations, provenance, and rebuildable retrieval projections.
3. **Memory**: durable user preferences, corrections, project decisions, terminology,
   source-quality notes, and reusable conclusions learned through conversation.
4. **Applications**: chat over knowledge, document Q&A, deep research, report generation,
   editing, and future wiki or briefing workflows.

Ingestion is progressive and evidence-first. The system creates stable source/chunk
artifacts and extraction candidates first. Candidates are validated against exact source
ranges before they become canonical graph records. Sources are analyzed more deeply only
when a user question or agent task requires additional detail.

## System Architecture

```text
Next.js knowledge workspace
  -> FastAPI service
       -> authenticates and authorizes users
       -> reads and writes product state
       -> coordinates uploads and creates background tasks
  -> durable task queue
       -> Python worker service
            -> ingestion, agent tasks, connector sync, memory, and reports
            -> DeepAgents harness
            -> persists results and product events
  -> Realtime / WebSocket event delivery
       -> streams persisted task updates to the frontend
```

The durable system of record is PostgreSQL. Object storage owns uploaded sources,
extracted content, connector snapshots, and generated artifacts. V1 runs one worker
service with several job handlers; specialized ingestion, agent, connector, memory, and
export workers can be split out later when scaling requires it.

LangChain DeepAgents is the agent engine. It provides planning, tools, filesystem access,
subagents, interrupts, checkpoints, and streaming. This repository owns the product
contracts, persistence, source provenance, evidence graph, memory policy, connectors,
retrieval, and user applications around that engine.

## V1 Deployment

V1 uses managed Supabase services with ordinary Docker containers for the application
runtime:

```text
Next.js web                 -> Vercel
FastAPI API                 -> container runtime
agent/ingestion worker      -> container runtime
Postgres + pgvector         -> Supabase Database
authentication             -> Supabase Auth
object storage              -> Supabase Storage
durable task queue          -> Supabase Queues (pgmq)
live product events         -> Supabase Realtime
```

Provider-specific code remains behind small interfaces. The same components can later
map to AWS ECS Fargate, Aurora/RDS PostgreSQL, S3, SQS, Cognito, Secrets Manager, and API
Gateway WebSockets or AppSync without changing domain contracts.

## Repository Layout

```text
apps/web                  Next.js knowledge workspace
services/api              FastAPI command/query and WebSocket service
services/worker           Background agent and ingestion worker
packages/harness_core     DeepAgents adapter, product events, and tool bridges
packages/knowledge_core   Platform contracts, evidence, graph, memory, and connectors
packages/research_core    Research and report applications built on the platform
docs                      Product, architecture, data model, and delivery plans
```

## Delivery Milestones

1. **Knowledge Platform Spine**: shared platform contracts and DeepAgents adapter.
2. **Runtime Shell**: API, worker, persistence, queue, storage, events, Docker, and CI.
3. **Ingestion, Tools, and Connectors**: local uploads, web sources, progressive
   ingestion, source deepening, evidence validation, and connector contracts.
4. **Knowledge and Memory Workflow**: chat over knowledge, memory extraction, approval,
   retrieval, corrections, and conflict handling.
5. **Deep Research Applications**: planner, research subagents, Search as Code, briefings,
   and research outputs.
6. **Reports, Citations, and Editing**: report editor, visual assets, citations, editor
   suggestions, and exports.

## Initial Implementation Order

1. Shared platform models such as `AgentTask`, `ProductEvent`, `Asset`, `KnowledgeFile`,
   `GraphNode`, `MemoryRecord`, and `SourceConnector`.
2. DeepAgents harness adapter and deterministic fake adapter.
3. PostgreSQL schema, migrations, and repository interfaces.
4. Queue, object-storage, identity, and event-publisher interfaces.
5. API/worker task lifecycle and realtime event delivery.
6. Local multimodal upload and shallow ingestion pipeline.
7. Chat over project knowledge with citations and targeted source deepening.
8. Conversation-derived memory and correction workflows.
9. First external source connector.
10. Deep research and report applications.

## Design Documents

- [`docs/platform-restructure-plan.md`](docs/platform-restructure-plan.md): product
  direction and revised build order.
- [`docs/product-plan.md`](docs/product-plan.md): workflows and milestones.
- [`docs/architecture.md`](docs/architecture.md): services, persistence, events, and
  connector/memory architecture.
- [`docs/data-model.md`](docs/data-model.md): ERD and table-level design.
- [`docs/knowledge-graph-design.md`](docs/knowledge-graph-design.md): evidence lifecycle,
  graph validation, provenance, projections, and retrieval policy.
- [`docs/deepagents-system-design.md`](docs/deepagents-system-design.md): DeepAgents
  integration and execution boundary.
- [`docs/source-connectors.md`](docs/source-connectors.md): connector families, sync model,
  permissions, and rollout order.
- [`docs/deployment-strategy.md`](docs/deployment-strategy.md): V1 Supabase deployment and
  AWS migration shape.
- [`docs/frontend-workspace.md`](docs/frontend-workspace.md): knowledge workspace and
  report application UI.

## Current Status

The platform architecture, evidence model, deployment strategy, milestones, and GitHub
issue structure are defined. The repository contains the initial Python service/package
skeleton, tests, Docker scaffolding, and CI. Shared platform contracts, DeepAgents adapter
work, tool integration, and a minimal knowledge-chat path are currently being developed
through focused pull requests.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The Docker Compose stack and frontend package are still skeletal. They will be expanded
as the runtime, persistence, ingestion, and knowledge-workspace milestones are
implemented.
