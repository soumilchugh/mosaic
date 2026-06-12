# Product Plan

## Goal

Build a deep research system on LangChain DeepAgents. DeepAgents provides the agent
harness capabilities: planning, tool use, context management, subagents, streaming,
permissions, and human-in-the-loop control. Our product layer supplies research-specific
run contracts, tools, source/report graphs, citations, and the frontend event stream.

## V1 Workflow

1. User submits research intent, local documents, web preferences, output style, and depth.
2. Planner performs fast reconnaissance and proposes topics plus an outline.
3. User approves or edits topics before deeper research begins.
4. Researcher agents explore topics using breadth-first, depth-first, or hybrid strategy.
5. Search as Code can fan out web, document, connector, and codebase retrieval programs
   inside a bounded sandbox when the question requires broad evidence gathering.
6. Sources are processed into a source graph in real time.
7. Writer streams Markdown sections once evidence thresholds are met.
8. Editor reviews draft sections against the source graph and suggests improvements.
9. User receives a final Markdown report with citations and generated artifacts.

## Delivery Principles

- Use DeepAgents as the agent engine instead of rebuilding an agent runtime.
- Keep our DeepAgents adapter thin, typed, and replaceable.
- Use typed event contracts between API, worker, frontend, and DeepAgents streams.
- Prefer thin research tools first, then deepen each tool behind a stable interface.
- Tie every substantial feature to a GitHub issue and PR.
- Require CI on every PR from the beginning.

## Milestones

### M1: Harness Spine

- Adopt DeepAgents as the V1 harness.
- Study and map DeepAgents SDK capabilities to the product architecture.
- Define product-level research run, task, and event contracts.
- Define an adapter boundary around DeepAgents.
- Map DeepAgents stream events into product events.
- Prove one minimal SDK-backed run with deterministic tests.

### M2: Runtime Shell

- Add FastAPI service with run creation and health endpoints.
- Add worker entrypoint and queue abstraction.
- Add Docker Compose for API, worker, Postgres, Redis, Neo4j, MinIO, and web.
- Add CI for Python lint/type/test and frontend checks.

### M3: Tool Foundation

- DeepAgents composite backend and virtual filesystem layout.
- Filesystem/document ingestion tool.
- Web search/scrape tool abstraction.
- Search as Code retrieval runner.
- Codebase ingestion/search/citation tools.
- DeepAgents-compatible permission policy for tool calls.
- Upload and artifact transfer pipeline.
- Structured tool errors and trace events.

### M4: Research Workflow

- DeepAgents subagent roster and role-specific skills.
- Search program runner and code researcher subagents.
- Planner topic proposal.
- Topic approval intervention.
- Research frontier strategy.
- Streaming Markdown section writer.

### M5: Graph, Citations, Editing

- Source graph model.
- Report graph model.
- Citation model.
- Editor criteria and suggestion events.

## Initial Open Questions

- Which DeepAgents model provider should be wired first for local development?
- Which search provider should be wired first?
- Should Neo4j be mandatory in local dev or support degraded mode?
- Should model/provider keys be user-supplied in V1?
- Which citation style should V1 default to?
- Should slide export remain a stub until after V1?
