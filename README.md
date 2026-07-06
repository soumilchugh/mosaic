# Agent Harness

Private working repo for a local-first agentic knowledge and deep research system.

The product goal is to build a multimodal knowledge and memory platform on LangChain
DeepAgents. Local files, connected sources, conversations, and agent work become an
evidence-first knowledge base that supports citation-backed chat, deep research, and a
Markdown report editor.

## Repository Layout

```text
apps/web                  Next.js frontend workspace
services/api              FastAPI backend
services/worker           Background research worker
packages/harness_core     DeepAgents adapter, product events, tool bridges
packages/knowledge_core   Assets, ingestion, evidence graph, retrieval, memory, connectors
packages/research_core    Planner/researcher/writer/editor workflows and graph models
docs                      Product, architecture, and delivery planning
```

V1 uses Supabase Cloud for managed Postgres, Auth, Storage, Realtime, and Queues while
FastAPI and long-running agent workers run as ordinary containers. See
[docs/deployment-strategy.md](docs/deployment-strategy.md).

## First Milestones

1. Harness spine: DeepAgents integration, app run/event contracts, and SDK adapter.
2. Runtime services: FastAPI API, worker process, Docker Compose, and CI.
3. Knowledge foundation: ingestion, exact provenance, extraction candidates, retrieval,
   and memory.
4. Research workflow: planner, topic approval, researcher loop, and streaming writer.
5. Reports and citations: report graph, citation validation, and editor checks.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The Docker Compose stack is intentionally skeletal in the first commit and will be
filled in as the API, worker, data stores, and frontend mature.
