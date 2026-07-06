# Product Plan

## Goal

Build an agentic multimodal knowledge and memory platform on LangChain DeepAgents.
DeepAgents provides the agent harness capabilities: planning, tool use, context
management, subagents, streaming, permissions, memory, and human-in-the-loop control.
Our product layer turns user files, connected sources, conversations, and agent work into
a living knowledge base that can answer questions, deepen sources, produce reports, and
support future applications.

Deep research and report generation are important applications on top of the platform,
not the whole product.

## Platform Model

The core platform has four layers:

1. **Sources and assets**: uploaded files, web pages, code repositories, Slack threads,
   team tools, knowledge apps, work management systems, future databases/APIs, generated
   artifacts, and exports.
2. **Knowledge base**: shallow source cards, topic cards, knowledge files, graph nodes,
   graph edges, chunks, claims, facts, entities, citations, and source ranges.
3. **Memory layer**: durable user preferences, project decisions, corrections,
   instructions, reusable conclusions, and links back to the messages or sources that
   produced them.
4. **Applications**: chat/Q&A, deep research, report generation, report editing, wiki
   generation, source comparison, code understanding, briefings, and exports.

## V1 Workflows

### Upload And Chat

1. User uploads local documents, images, spreadsheets, or code snapshots.
2. API stores originals as assets and records provenance.
3. Worker performs shallow ingestion into knowledge files and graph records.
4. User asks questions immediately.
5. Agent searches existing knowledge first.
6. If needed, agent reads targeted ranges from the original asset and deepens the
   knowledge base.
7. Answer is saved with citations, and reusable corrections or decisions can become
   memories.

### Connector Ingestion

1. User connects an external source such as Slack, GitHub, Notion, Google Drive, or a web
   source.
2. Connector syncs source records into assets and source metadata.
3. Worker creates shallow knowledge cards and graph records.
4. Future syncs update changed records and preserve source provenance.
5. Agent can answer from connector knowledge or deepen specific threads/files when a
   question requires more detail.

Connector support should start with local uploads and web URLs, then expand to GitHub,
Slack, Notion/Drive, Linear/Jira, email/calendar, and structured databases/APIs. See
[source-connectors.md](source-connectors.md) for the detailed source strategy.

### Deep Research

1. User asks for deeper investigation over existing knowledge plus optional external
   sources.
2. Worker assembles a bounded context pack from conversation history, memories, graph
   results, knowledge files, assets, and DeepAgents checkpoint state.
3. Planner proposes a research path or asks for approval when scope is ambiguous.
4. Researcher agents explore known sources first, then web/connectors/code as needed.
5. Search as Code can fan out retrieval programs inside a bounded sandbox.
6. New useful evidence updates the knowledge base and memory layer.
7. Output can be an answer, briefing, report outline, report draft, or updated wiki.

### Report Generation And Editing

1. User asks to turn knowledge into a report or memo.
2. Writer streams Markdown sections once evidence is sufficient.
3. Editor reviews sections against the source graph and memory layer.
4. User edits in a workspace with chat controls, evidence panels, graph panels, and visual
   asset blocks.
5. Final report remains connected to citations, source chunks, assets, and memories.

## Delivery Principles

- Use DeepAgents as the agent engine instead of rebuilding an agent runtime.
- Keep our DeepAgents adapter thin, typed, and replaceable.
- Use typed event contracts between API, worker, frontend, and DeepAgents streams.
- Prefer shallow ingestion first, then deepen sources only when a user question or
  application needs more detail.
- Treat model-extracted nodes, claims, aliases, and relationships as candidates until
  typed validation and exact source evidence allow promotion.
- Keep Postgres canonical and treat vector and graph databases as rebuildable projections
  with stable product IDs.
- Route queries to lexical, vector, graph, or hybrid retrieval and require measured value
  before adding graph latency to a query class.
- Treat chat, memory creation, source ingestion, and graph updates as first-class product
  behavior.
- Tie every substantial feature to a GitHub issue and PR.
- Require CI on every PR from the beginning.

## Milestones

### M1: Knowledge Platform Spine

- Adopt DeepAgents as the V1 harness.
- Study and map DeepAgents SDK capabilities to the product architecture.
- Define product-level agent task, ingestion task, memory task, research task, and event
  contracts.
- Define an adapter boundary around DeepAgents.
- Map DeepAgents stream events into product events.
- Prove one minimal SDK-backed chat/knowledge run with deterministic tests.

### M2: Runtime Shell

- Add product persistence for users, projects, knowledge scopes, conversations, messages,
- assets, memories, source connectors, runs, events, interventions, and DeepAgents thread
  mappings.
- Add FastAPI service with project, conversation, asset, ingestion, memory, and agent task
  endpoints.
- Add worker entrypoint and queue abstraction.
- Add context pack assembly for starting/resuming DeepAgents runs.
- Add Docker Compose for API, worker, web, Postgres with pgvector/pgmq, and local object
  storage.
- Add provider boundaries for Supabase Postgres/Auth/Storage/Realtime/Queues and future
  Aurora/S3/Cognito/SQS equivalents.
- Add CI for Python lint/type/test and frontend checks.

### M3: Ingestion, Tools, And Connectors

- DeepAgents composite backend and virtual filesystem layout.
- Filesystem/document ingestion tool.
- Multimodal asset ingestion pipeline for documents, images, tables, and code snapshots.
- Source connector contract for Slack, GitHub, web, and future external systems.
- Web search/scrape tool abstraction.
- Search as Code retrieval runner.
- Codebase ingestion/search/citation tools.
- File-native graph repository and progressive ingestion states.
- Evidence-first extraction candidate, validation, and promotion workflow.
- Structured source ranges and citation round-trip validation.
- Entity alias, merge-candidate, and reversible merge records.
- Versioned graph node/edge schemas, temporal claims, corrections, and supersession.
- Rebuildable chunk embeddings and projection version tracking.
- Graph-guided retrieval tools that return source/code result sets.
- Retrieval strategy router and auditable result-set contract.
- Ingestion, graph extraction, citation, and retrieval evaluation fixtures.
- DeepAgents-compatible permission policy for tool calls.
- Upload and artifact transfer pipeline.
- Structured tool errors and trace events.

### M4: Knowledge And Memory Workflow

- Chat/Q&A over project and global knowledge scopes.
- Memory extraction policy for preferences, corrections, decisions, reusable facts, and
  source notes.
- User approval flow for sensitive or high-impact memories.
- Memory retrieval and conflict handling during context assembly.
- Progressive source deepening from user questions.
- Knowledge maintenance flows for stale, corrected, or superseded sources.

### M5: Deep Research Applications

- DeepAgents subagent roster and role-specific skills.
- Search program runner and code researcher subagents.
- Planner topic proposal.
- Topic approval intervention.
- Research frontier strategy.
- Answer, briefing, and report-outline outputs.

### M6: Reports, Citations, And Editing

- Source/code graph model.
- File-native graph projection.
- Report graph model.
- Citation model.
- Report editor workspace with visual asset blocks.
- Editor criteria and suggestion events.

## Initial Open Questions

- Which DeepAgents model provider should be wired first for local development?
- Which search provider should be wired first?
- What measured workload would justify adding Neo4j instead of the Postgres graph
  repository?
- Should model/provider keys be user-supplied in V1?
- Which citation style should V1 default to?
- Should slide export remain a stub until after V1?
- Should user-global knowledge be enabled in V1 or should V1 start project-local only?
- Should one conversation map to one DeepAgents thread, or should every research run
  create a child thread?
- Which source connector should come first after local uploads and web URLs: GitHub,
  Slack, Notion, or Google Drive?
- Which memory writes require explicit user approval in V1?
- Should memory be stored as graph nodes only, or as a dedicated table plus graph
  projection?
