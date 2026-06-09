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
postgres   Runs, reports, metadata
redis      Queue, pub/sub, transient state
neo4j      Source and report graphs
minio      Local object storage
```

## API Shape

```text
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
