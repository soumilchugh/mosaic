# DeepAgents System Design

## Purpose

This document maps DeepAgents SDK capabilities to the agentic knowledge and memory
platform. The goal is to use the SDK as the agent harness rather than rebuilding
planning, tool execution, filesystem, subagents, interrupts, memory, or streaming.

Deep research, chat/Q&A, report generation, source ingestion, source deepening, and
memory extraction should all run through the same harness boundary.

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

DeepAgents owns agent execution. Our product owns knowledge, memory, source provenance,
and application semantics.

```text
API / Worker
  -> AgentTask
  -> HarnessAdapter
  -> DeepAgents agent
  -> DeepAgents stream / interrupts / files / memory
  -> ProductEvent stream
  -> API persistence + WebSocket frontend
```

The API and frontend should not depend on DeepAgents-native stream objects directly.
Everything becomes a product contract first.

## Product Persistence And Sessions

The product needs durable user, project, knowledge-scope, conversation, asset, connector,
memory, event, and graph state outside of DeepAgents. DeepAgents should be resumable
through product-owned IDs, but it should not be the only source of truth for user-visible
history.

Postgres is the V1 system of record:

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
ingestion_runs
```

Object storage owns file bytes:

```text
uploaded PDFs/docs/images
connector snapshots from Slack/GitHub/Drive/Notion/web
fetched web source snapshots
generated reports
charts/images/slides
code archives or repository snapshots
```

`assets` records in Postgres point to MinIO/S3 object URIs, content hashes, MIME types,
owners, project IDs, knowledge scope IDs, and source provenance.

DeepAgents thread and checkpoint state should be keyed by product IDs:

```text
conversation_id -> default DeepAgents thread_id
agent_task_id -> task-specific DeepAgents thread_id when isolation is useful
research_run_id -> research-specific child thread_id
intervention_request_id -> interrupt/resume correlation
```

This lets the product resume conversations, continue interrupted agent work, and rebuild
the visible timeline even if a worker restarts.

## Context Pack Assembly

Before each DeepAgents invocation, the worker should assemble a bounded context pack from
persisted product state:

1. conversation summary
2. recent messages
3. active agent task or application state
4. pending interventions
5. relevant memory records and memory links
6. relevant project and knowledge-scope metadata
7. graph-guided retrieval result sets
8. selected source/code cards and topic files
9. connector and asset metadata plus accessible workspace paths
10. DeepAgents thread/checkpoint ID

The context pack is the bridge between session persistence and agent execution. It keeps
inputs bounded while still grounding the agent in prior work.

Context assembly should be deterministic enough to audit:

- record graph queries and result IDs used for each run step
- record selected files/cards included in context
- preserve the event that triggered assembly
- avoid loading raw assets unless the graph/source card indicates the agent should inspect
  them

DeepAgents owns internal execution state; the product owns the recoverable context recipe,
memory projection, knowledge projection, and user-visible timeline.

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

The first local implementation uses the provider-neutral filesystem object-store adapter.
It writes bucket-style `object://` URIs and mounts one durable object volume into both the
API and worker containers. Production S3, MinIO, or Supabase adapters implement the same
storage contract. Workers materialize selected records under `/workspace/uploads/`; files
written under `/artifacts/` return through the same service and create an
`artifact.generated` product event.

## Live Knowledge Workspace And Graph

The knowledge system should combine agent-readable files with a graph/index projection.
The graph is not expected to decide whether evidence is relevant. It should return
structured results that describe what the system currently knows. The agent evaluates
those results and decides whether to answer, search again, or deepen original sources.
The canonical graph is evidence-first: extraction agents write candidates, not trusted
facts, and every promoted semantic record remains connected to exact source evidence.
See [knowledge-graph-design.md](knowledge-graph-design.md) for the canonical lifecycle,
identity, validation, temporal, and retrieval contracts.

```text
Raw source or repository
  -> shallow source/code card
  -> structured source chunks
  -> extraction candidates
  -> validation and entity resolution
  -> canonical source-relative graph
  -> graph-guided retrieval results
  -> agent evaluation
  -> targeted deepening when needed
  -> updated files and graph
```

The graph response should be mechanical and provenance-rich:

```json
{
  "nodes": [
    {
      "id": "source_017",
      "type": "source",
      "summary_path": "/workspace/sources/source_017.md",
      "raw_path": "/artifacts/source_017.pdf",
      "known_ranges": ["59-80"],
      "known_chunks": ["chunk_017_12", "chunk_017_13"],
      "known_claims": ["claim_201"],
      "edges": ["COVERS_TOPIC", "MENTIONS_ENTITY"],
      "ingestion_level": "shallow_card"
    }
  ],
  "paths": [],
  "metadata": {
    "query_id": "query_042",
    "snapshot": "2026-06-13T14:30:00Z"
  }
}
```

The graph should avoid language such as "likely relevant" or "probably contains." It
returns known nodes, edges, file paths, chunks, page ranges, and source references. The
agent decides relevance and sufficiency.

Similarity, retrieval score, and extraction confidence must remain distinct:

- similarity estimates whether two representations are close
- retrieval score ranks a result for a query
- extraction confidence records uncertainty in an extraction process
- evidence status records whether a source range supports or contradicts a claim

Only the last of these can justify a citation.

### Progressive Ingestion

Each source should start cheap and become richer only when work requires it.

```text
0 discovered
1 shallow_card          high-level summary, topics, entities, outline, raw pointer
2 section_indexed       headings/page ranges/section summaries
3 topic_deepened        selected sections read for a specific topic
4 claim_extracted       claims, citations, contradictions, confidence
5 exhaustively_indexed  rare, source fully processed
```

New PDFs, web pages, files, repositories, and connector records should first produce
shallow cards. A 100-page PDF should not be exhaustively analyzed by default. The system
should preserve enough structure for future retrieval:

- high-level summary
- known topics and entities
- table of contents or inferred outline
- page/section hints where cheap
- raw file pointer
- ingestion level and covered ranges
- links to topic files and graph nodes

When a future question needs missing detail, the agent can call a deepening tool:

```python
await ctx.ingestion.deepen_source(
    source_id="source_017",
    topic="software supply chain",
    ranges=["59-80"],
    mode="claims_and_citations",
    budget={"max_pages": 20, "max_minutes": 4},
)
```

The deepening tool updates the source card, topic file, chunks, claims, graph edges, and
search indexes. Future runs benefit from the learned structure.

### File-Native Graph Projection

Files remain the agent-facing workspace:

```text
/workspace/research_map.md
/workspace/topics/<topic>.md
/workspace/sources/<source>.md
/workspace/code/<repo>/<commit>/repo_card.md
/workspace/report/<section>.md
```

The graph indexes and connects these files:

```text
Topic -> COVERED_BY -> TopicFile
Source -> DESCRIBED_BY -> SourceCard
Source -> HAS_CHUNK -> Chunk
Chunk -> SUPPORTS -> Claim
Claim -> ABOUT -> Topic
Claim -> CONTRADICTS -> Claim
Claim -> SUPERSEDES -> Claim
Repository -> HAS_FILE -> CodeFile
CodeFile -> DEFINES -> Symbol
Symbol -> DEPENDS_ON -> Symbol
ReportSection -> CITES -> Source/Chunk/CodeReference
```

This gives the agent a reliable starting point without forcing every raw source to be
fully extracted up front.

## Search As Code

Inspired by Perplexity's "Search as Code" architecture, deep research should treat search
as a programmable workflow rather than a single query tool call. The agent should be able
to write and run retrieval plans in the sandbox, observe partial results, and change
course when evidence quality is weak.

The product should support a `search-program-runner` tool/subagent that can:

- decompose a research question into many targeted retrieval tasks
- run web, document, connector, and codebase searches in parallel
- retry or expand searches when source quality is low
- dedupe, join, rank, and filter results in code before sending them back to the model
- track every source, score, query, and transformation for citation/debugging
- merge live web and authorized internal sources in the same run

This should run inside the sandbox, near the agent, with strict limits:

- bounded parallelism
- per-run compute/time budgets
- allowlisted connectors
- no unapproved external side effects
- all source provenance preserved

The research graph should store both raw retrieved sources and derived search-program
metadata:

```text
ResearchQuery
  -> SearchProgram
  -> RetrievalStep
  -> RetrievedSource
  -> RankedEvidence
```

This gives the editor and citation layer enough information to explain why a source was
used, what query found it, and whether conflicting sources were considered.

Search programs should query the graph first. If the graph returns weak or empty current
knowledge, the program can search source cards, raw files, web/connectors, or code
repositories, then deepen the graph with any newly discovered information.

## Codebase Research

Code repositories should be a first-class research corpus alongside local documents and
web sources. This is separate from "Search as Code": Search as Code is how retrieval is
planned and executed; codebase research is one kind of source it can search.

Use a dedicated `code-researcher` subagent for questions such as:

- "Where is authentication enforced?"
- "Which services depend on this model?"
- "What changed between these releases?"
- "Which vulnerabilities affect our stack?"
- "How does this API work end to end?"

The code search stack should combine:

- lexical search using `ripgrep`-style exact matching
- filename/path search
- symbol extraction for functions/classes/types/routes
- dependency graph traversal
- optional semantic code embeddings
- commit/PR/release metadata where connected
- sandboxed test or static-analysis execution when approved

Codebase ingestion should preserve provenance:

```text
Repository
  -> Commit
  -> File
  -> Symbol
  -> CodeChunk
  -> Dependency
  -> Finding
```

Code search results should cite file paths, line numbers, commit SHAs, and repository
URLs when available. Generated answers should distinguish observed code facts from model
inferences.

Codebase research follows the same progressive ingestion loop:

```text
Repository connected
  -> repo_card.md with purpose, languages, packages, entry points
  -> shallow graph nodes for files, symbols, routes, dependencies
  -> graph search returns file/symbol references
  -> agent inspects exact files/lines when needed
  -> deeper symbol/dependency/test findings are written back
```

The first pass should avoid full semantic analysis of every file. It should index the
repository map, file tree, dependency manifests, route definitions, public symbols, and
README/docs. Deeper passes are triggered by questions:

- trace an API end to end
- explain a module boundary
- identify vulnerable dependencies
- compare two commits
- find call sites or data flow for a symbol

The code graph should return result sets such as files, symbols, references, commit SHAs,
and line ranges. The `code-researcher` decides which files to read and whether to update
the graph with newly discovered relationships.

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

- users, projects, knowledge scopes, conversations, messages, and assets in Postgres
- `ResearchRun` state in Postgres
- event stream in Postgres
- intervention requests and resume decisions in Postgres
- uploaded/generated artifacts in object storage
- DeepAgents checkpoints through a durable LangGraph checkpointer
- long-term memory through `StoreBackend` or equivalent durable backend
- source/report graphs in Neo4j or a graph repository abstraction

Short-term context and large tool outputs should stay in the DeepAgents backend. Product
events should store the durable user-visible projection, not every internal token.

V1 can implement the graph repository in Postgres tables first:

```text
graph_schema_versions
graph_nodes / graph_edges / graph_chunks
graph_candidates / graph_candidate_evidence
graph_entity_aliases / graph_entity_merges
graph_embeddings
graph_retrieval_runs
ingestion_runs
```

Neo4j can be added later as a projection if multi-hop relationship queries outgrow the
Postgres graph repository. Full-text, vector, and Neo4j records are rebuildable
projections keyed by canonical Postgres UUIDs. The adapter should keep the agent-facing
graph tools stable.

## Subagent Design

Use DeepAgents subagents for isolated roles:

- `planner`: fast reconnaissance, topic proposals, outline
- `local-document-researcher`: uploaded document analysis
- `web-researcher`: web search, source ranking, scraping
- `search-program-runner`: sandboxed Search as Code retrieval orchestration
- `code-researcher`: repository search, symbol/dependency analysis, code citations
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
/skills/search-as-code/
/skills/code-research/
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
Search program steps      -> research.query_started / source.found / source.ranked
Code search results       -> code.symbol_found / code.reference_added / source.found
DeepAgents output         -> run.completed / report.completed
DeepAgents errors         -> run.failed / subagent.failed / tool.failed
```

The frontend should use product event types only. DeepAgents stream details can be stored
in trace metadata for debugging.

## Implementation Order

1. Study and lock the DeepAgents integration contract.
2. Add DeepAgents dependency and adapter interface.
3. Define user, workspace, conversation, asset, run, event, and intervention contracts.
4. Add durable DeepAgents thread/checkpoint mapping.
5. Add context pack assembly from conversation, graph, assets, and knowledge files.
6. Build a minimal DeepAgents-backed run with one simple tool.
7. Add backend factory with local `CompositeBackend`.
8. Add permission policy and HITL resume flow.
9. Add upload/artifact seeding and retrieval.
10. Add structured source ranges and the canonical Postgres graph repository.
11. Add versioned graph schemas plus extraction candidate validation and promotion.
12. Add entity aliases, deterministic identity, and reversible merge decisions.
13. Add chunk full-text/vector projections and projection version tracking.
14. Add a retrieval router and auditable result-set contract.
15. Add bounded graph traversal only for evaluated relationship and multi-hop queries.
16. Add ingestion, graph, retrieval, and citation evaluation fixtures.
17. Add Search as Code runner with bounded sandbox execution.
18. Add codebase research ingestion/search/citation tools.
19. Add subagent roster and event mapping.
20. Add skills directory and read-only skills route.
21. Add durable checkpointer/store integration.

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
- Which internal connectors should Search as Code support first?
- Should codebase search be local-only first, GitHub-backed first, or both?
- What budget limits should apply to generated search programs?
- Should the initial graph repository be Postgres-only, or should Neo4j be available as
  an optional projection from day one?
- Which graph candidate types can be promoted automatically, and which require review?
- Which query classes show enough measured gain from graph traversal to enable it by
  default?
- Which domain identifiers are strong enough for deterministic entity resolution in V1?
- What minimum shallow card fields are required before a source is useful for graph
  retrieval?
- Should conversation-level and research-run-level DeepAgents threads be separate from
  the start, or should every research run own a child thread under a conversation?
- How aggressively should old messages be summarized versus kept in direct context?

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
- Perplexity blog paste: "Deep Research, now in Computer" published June 11, 2026
