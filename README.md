# Agent Harness

Private working repo for a local-first deep research agent system.

The product goal is to build a deep research system on LangChain DeepAgents, combining
local document research, web research, live event streaming, source/report graphs, and a
Markdown report editor.

## Repository Layout

```text
apps/web                  Next.js frontend workspace
services/api              FastAPI backend
services/worker           Background research worker
packages/harness_core     DeepAgents adapter, product events, tool bridges
packages/research_core    Planner/researcher/writer/editor workflows and graph models
docs                      Product, architecture, and delivery planning
```

## First Milestones

1. Harness spine: DeepAgents integration, app run/event contracts, and SDK adapter.
2. Runtime services: FastAPI API, worker process, Docker Compose, and CI.
3. Tool foundation: filesystem, web/search, document ingestion, and DeepAgents permissions.
4. Research workflow: planner, topic approval, researcher loop, and streaming writer.
5. Graph and citations: source graph, report graph, citation model, and editor checks.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The Docker Compose stack is intentionally skeletal in the first commit and will be
filled in as the API, worker, data stores, and frontend mature.
