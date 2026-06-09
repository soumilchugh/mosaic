# DeepAgents System Design

## Purpose

This document maps DeepAgents SDK capabilities to the deep research product. The goal is
to use the SDK as the agent harness rather than rebuilding planning, tool execution,
filesystem, subagents, interrupts, memory, or streaming.

## SDK Capabilities We Should Use

DeepAgents provides:

- built-in planning through `write_todos`
- custom functions, LangChain tools, and MCP tools
- built-in filesystem tools: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
- sandbox-backed shell execution through `execute`
- pluggable filesystem backends
- filesystem permissions with allow, deny, and interrupt modes
- subagents and async subagents
- DeepAgents event streaming for messages, tool calls, values, output, and subagents
- human-in-the-loop interruption and resume through LangGraph checkpoints
- long-term memory through filesystem-backed memory and LangGraph stores
- skills loaded progressively from `SKILL.md` directories
- sandbox file transfer APIs for uploaded inputs and generated artifacts

## Product Boundary

DeepAgents owns agent execution. Our product owns research semantics.

```text
API / Worker
  -> ResearchTask
  -> HarnessAdapter
  -> DeepAgents agent
  -> DeepAgents stream / interrupts / files / memory
  -> Product ResearchEvent stream
  -> API persistence + WebSocket frontend
```

The API and frontend should not depend on DeepAgents-native stream objects directly.
Everything becomes a product contract first.

## Filesystem And Backend Strategy

Use a composite virtual filesystem:

```text
/workspace/      uploaded documents, generated report drafts, user-visible working files
/artifacts/      generated exports, charts, tables, images, slide drafts
/memories/       durable user/project/organization memory
/skills/         read-only skill directories
/scratch/        run-local scratch files and large tool outputs
```

Recommended V1 mapping:

- `/scratch/`: DeepAgents `StateBackend`
- `/workspace/`: object-storage-backed custom backend or sandbox backend
- `/artifacts/`: object-storage-backed custom backend
- `/memories/`: `StoreBackend` or custom durable backend
- `/skills/`: read-only filesystem/backend route seeded by application code

For local development, we can start with `CompositeBackend` plus `StateBackend` and a
local `FilesystemBackend(root_dir=..., virtual_mode=True)` for `/workspace/`. Production
should avoid direct host filesystem access from the API process.

## Sandboxes

Use the "sandbox as tool" pattern:

- The worker runs the DeepAgents agent.
- Shell/file execution happens through a sandbox backend.
- API keys and product persistence stay outside the sandbox.
- Sandbox failures do not erase product state.

V1 can start without shell execution for pure research. Add sandbox execution when we need:

- PDF/table extraction that benefits from local code
- chart generation
- report export pipelines
- slide generation
- deterministic skill scripts

Sandbox lifecycle should be thread-scoped by default: one sandbox per research run/thread
with a TTL. Longer-lived assistant-scoped sandboxes can come later for organization
knowledge libraries or repeated code/data tasks.

## Asset Uploads And Artifacts

Uploaded assets should flow through the product, not directly through an LLM tool call.

1. User uploads files to API.
2. API stores originals in object storage.
3. API records artifact metadata in Postgres.
4. Worker seeds DeepAgents backend/sandbox with the files under `/workspace/uploads/`.
5. Agent reads files using DeepAgents filesystem tools.
6. Generated files are written under `/artifacts/`.
7. Worker downloads or reads generated artifacts and stores them in object storage.
8. Product emits `artifact.generated` events.

For sandbox-backed runs, use DeepAgents sandbox backend transfer APIs to seed files before
execution and retrieve generated artifacts after execution.

## Permissions And HITL

Use DeepAgents filesystem permissions for path-level access:

- allow read/write under `/workspace/**`
- allow write under `/artifacts/**`
- deny reads and writes to secrets and config paths
- deny writes to `/skills/**`
- deny or interrupt writes to `/memories/**`
- interrupt risky artifact exports or external side effects

Use DeepAgents/LangGraph human-in-the-loop interrupts for:

- topic/outline approval
- tool calls with external side effects
- protected filesystem writes
- memory updates
- high-cost web searches or long-running jobs
- publishing/export actions

The product should persist each interrupt as an `InterventionRequest`, expose it over
WebSocket, and resume with approve/edit/reject decisions using the same DeepAgents thread
ID/checkpointer state.

## Conversation Persistence

DeepAgents requires stable thread IDs for resumed conversations and interrupts. Our run ID
should be the primary thread ID unless we later split one research run into multiple
threads.

Persist:

- `ResearchRun` state in Postgres
- event stream in Postgres
- uploaded/generated artifacts in object storage
- DeepAgents checkpoints through a durable LangGraph checkpointer
- long-term memory through `StoreBackend` or equivalent durable backend
- source/report graphs in Neo4j or a graph repository abstraction

Short-term context and large tool outputs should stay in the DeepAgents backend. Product
events should store the durable user-visible projection, not every internal token.

## Subagent Design

Use DeepAgents subagents for isolated roles:

- `planner`: fast reconnaissance, topic proposals, outline
- `local-document-researcher`: uploaded document analysis
- `web-researcher`: web search, source ranking, scraping
- `evidence-extractor`: entities, claims, facts, contradictions
- `writer`: Markdown section drafting
- `editor`: graph-aware review and suggestions
- `visualizer`: charts, diagrams, generated visual artifacts later
- `exporter`: Markdown to slides/PPTX later

Keep each subagent's tools minimal. Use subagent-specific permissions and skills:

- research subagents can read `/workspace/**` and write `/scratch/**`
- writer can read evidence and write `/workspace/report/**`
- editor can read source/report graph projections and write suggestions
- skills are isolated per subagent where appropriate

Use async subagents for parallel web/local research topics once the single-run path is
stable.

## Skills

Use skills for reusable procedural knowledge, not for volatile run state.

Initial skill directories:

```text
/skills/source-evaluation/
/skills/citation-writing/
/skills/market-research/
/skills/technical-research/
/skills/report-structure/
/skills/slide-export/
```

Skills should be read-only by default. They can include:

- `SKILL.md` instructions
- small scripts for deterministic transformations
- templates
- evaluation rubrics
- citation/report style guides

The agent sees skill summaries first and loads full skill content only when relevant,
which helps keep context small.

## Thinking And Planning

Use DeepAgents' default planning behavior and `write_todos` as the internal planning
surface. The product should expose a curated projection:

- current phase
- active subagent
- visible todo/status summary
- sources found
- sections started/completed
- intervention requests

We should not stream private chain-of-thought. Any "thinking" shown to users should be a
safe summary of plan/status/evidence decisions.

## Event Mapping

Map DeepAgents event streams into product events:

```text
DeepAgents messages       -> run.message / report.delta / editor.suggestion
DeepAgents tool_calls     -> tool.called / tool.completed / source.found
DeepAgents subagents      -> subagent.started / subagent.completed / subagent.failed
DeepAgents interrupts     -> user_intervention.requested
DeepAgents output         -> run.completed / report.completed
DeepAgents errors         -> run.failed / subagent.failed / tool.failed
```

The frontend should use product event types only. DeepAgents stream details can be stored
in trace metadata for debugging.

## Implementation Order

1. Study and lock the DeepAgents integration contract.
2. Add DeepAgents dependency and adapter interface.
3. Define `ResearchTask`, `ResearchRun`, `ResearchEvent`, and `InterventionRequest`.
4. Build a minimal DeepAgents-backed run with one simple tool.
5. Add backend factory with local `CompositeBackend`.
6. Add permission policy and HITL resume flow.
7. Add upload/artifact seeding and retrieval.
8. Add subagent roster and event mapping.
9. Add skills directory and read-only skills route.
10. Add durable checkpointer/store integration.

## Key Open Questions

- Which model provider should be the default for local development?
- Which sandbox provider should be V1: Daytona, Modal, Runloop, AgentCore, LangSmith, or
  no shell sandbox initially?
- Should `/workspace/` map to object storage directly or be seeded into per-run sandbox
  storage?
- Which DeepAgents stream projections should we persist versus only forward live?
- How strict should memory-write approval be in V1?
- Should topic approval be modeled as a DeepAgents interrupt or as a product-level pause
  before the DeepAgents deep-research phase starts?

## References

- DeepAgents overview: https://docs.langchain.com/oss/python/deepagents/overview
- Tools: https://docs.langchain.com/oss/python/deepagents/tools
- Backends: https://docs.langchain.com/oss/python/deepagents/backends
- Permissions: https://docs.langchain.com/oss/python/deepagents/permissions
- Human-in-the-loop: https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
- Subagents: https://docs.langchain.com/oss/python/deepagents/subagents
- Skills: https://docs.langchain.com/oss/python/deepagents/skills
- Sandboxes: https://docs.langchain.com/oss/python/deepagents/sandboxes
- Event streaming: https://docs.langchain.com/oss/python/deepagents/event-streaming
