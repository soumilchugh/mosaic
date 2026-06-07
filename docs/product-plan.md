# Product Plan

## Goal

Build a deep research system on a focused agent harness. The system should ingest local
documents and web sources, maintain a live evidence graph, and stream a citation-backed
Markdown report while research continues.

## V1 Workflow

1. User submits research intent, local documents, web preferences, output style, and depth.
2. Planner performs fast reconnaissance and proposes topics plus an outline.
3. User approves or edits topics before deeper research begins.
4. Researcher agents explore topics using breadth-first, depth-first, or hybrid strategy.
5. Sources are processed into a source graph in real time.
6. Writer streams Markdown sections once evidence thresholds are met.
7. Editor reviews draft sections against the source graph and suggests improvements.
8. User receives a final Markdown report with citations and generated artifacts.

## Delivery Principles

- Keep the harness runnable before every tool is complete.
- Use typed event contracts between API, worker, frontend, and agent loop.
- Prefer thin tools first, then deepen each tool behind a stable interface.
- Tie every substantial feature to a GitHub issue and PR.
- Require CI on every PR from the beginning.

## Milestones

### M1: Harness Spine

- Define task/run state.
- Define event model.
- Define tool protocol and registry.
- Implement a minimal async agent loop.
- Add deterministic unit tests with mock tools.

### M2: Runtime Shell

- Add FastAPI service with run creation and health endpoints.
- Add worker entrypoint and queue abstraction.
- Add Docker Compose for API, worker, Postgres, Redis, Neo4j, MinIO, and web.
- Add CI for Python lint/type/test and frontend checks.

### M3: Tool Foundation

- Filesystem/document ingestion tool.
- Web search/scrape tool abstraction.
- Permission model for tool calls.
- Structured tool errors and trace events.

### M4: Research Workflow

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

- Which search provider should be wired first?
- Should Neo4j be mandatory in local dev or support degraded mode?
- Should model/provider keys be user-supplied in V1?
- Which citation style should V1 default to?
- Should slide export remain a stub until after V1?
