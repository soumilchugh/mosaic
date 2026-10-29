# V1 Deployment Strategy

## Decision

V1 uses Supabase Cloud for managed data services and ordinary containers for the Python
application runtime.

```text
Next.js web                 -> Vercel
FastAPI API                 -> container runtime
agent/ingestion worker      -> container runtime
Postgres + pgvector         -> Supabase Database
authentication             -> Supabase Auth
object storage              -> Supabase Storage
durable task queue          -> Supabase Queues (pgmq)
live database notifications -> Supabase Realtime
```

The first container host can be selected independently from the application design.
Railway, Render, Fly.io, and AWS ECS Fargate are compatible options because the API and
worker ship as normal Docker images.

Supabase Edge Functions do not run model loops, document ingestion, research jobs, or
sandbox work. Those jobs can exceed edge-function execution and memory limits and need a
long-running Python container with explicit cancellation and checkpointing.

## Responsibility Boundaries

### Supabase

- PostgreSQL system of record
- pgvector chunk embeddings when enabled
- pgmq-backed durable queues
- user authentication and JWT issuance
- private asset buckets and signed object URLs
- Realtime delivery of persisted product events
- backups and managed database operation

### FastAPI

- product command and query API
- JWT verification and project authorization
- validation of product contracts
- creation of conversations, tasks, uploads, and interventions
- replay of persisted product events
- signed upload/download coordination

### Worker Containers

- DeepAgents execution
- source ingestion and extraction
- graph candidate validation and promotion
- embedding and projection jobs
- deep research and report generation
- task cancellation, retry, heartbeat, and checkpoint handling

### Next.js

- knowledge workspace UI
- authentication flow using Supabase Auth
- API calls to FastAPI for product behavior
- Realtime subscription for task and product-event updates
- direct signed uploads to Supabase Storage when authorized by the API

## Portability Rules

Core domain and workflow code must not import Supabase clients. Provider-specific code
lives behind these interfaces:

```text
Database / repositories     Supabase Postgres -> Aurora/RDS Postgres
ObjectStore                 Supabase Storage  -> Amazon S3
TaskQueue                   Supabase pgmq     -> Amazon SQS
IdentityProvider            Supabase Auth     -> Amazon Cognito
EventPublisher              Supabase Realtime -> API Gateway WebSocket/AppSync/SNS
ContainerRuntime            initial host      -> AWS ECS Fargate
Secrets                     host secrets      -> AWS Secrets Manager
Observability               OpenTelemetry     -> CloudWatch/X-Ray or another backend
```

Additional rules:

- Use SQLAlchemy/Alembic or ordinary SQL migrations against PostgreSQL rather than making
  PostgREST the application persistence layer.
- Keep durable workflow state in product tables, not database triggers or Edge Functions.
- Store canonical object URIs and checksums rather than provider-specific public URLs.
- Treat full-text, vector, and graph indexes as rebuildable projections.
- Keep queue messages provider-neutral, versioned, small, and idempotent.
- Validate authorization in FastAPI and reinforce it with Postgres row-level security
  where useful; do not rely on client-side checks.

## Local Development

Docker Compose remains the default local workflow:

```text
web
api
worker
postgres with pgvector and pgmq
minio or an ObjectStore-compatible local backend
```

Local development does not require a hosted Supabase project. A Supabase CLI profile can
be added when Auth, Storage, Realtime, or row-level-security integration needs end-to-end
testing. In-memory queue, object-store, and identity adapters remain available for fast
unit tests.

Neo4j, MongoDB, and Redis are not mandatory V1 dependencies:

- Postgres owns the canonical evidence graph; Neo4j is an optional measured projection.
- Postgres JSONB covers flexible connector metadata; MongoDB adds no required V1
  capability.
- pgmq owns durable jobs and Postgres stores durable events. Redis can be introduced later
  only for a measured caching, coordination, or high-volume pub/sub need.

## AWS Migration Shape

The V1 services map to AWS without changing product contracts:

| V1 capability | AWS target |
| --- | --- |
| FastAPI and worker containers | ECS Fargate |
| Supabase Postgres/pgvector | Aurora or RDS PostgreSQL/pgvector |
| Supabase Queues/pgmq | SQS |
| Supabase Storage | S3 |
| Supabase Auth | Cognito |
| Supabase Realtime | API Gateway WebSockets or AppSync |
| scheduled tasks | EventBridge Scheduler |
| secrets | Secrets Manager |
| logs and traces | CloudWatch and X-Ray/OpenTelemetry |
| optional graph projection | Neptune or another evaluated graph backend |

Lambda remains suitable for short webhooks, scheduled triggers, and lightweight glue. It
is not the default runtime for long-running research and ingestion tasks.

## Explicit Non-Goals

- no MongoDB or DocumentDB in V1
- no mandatory Neo4j in V1
- no agent execution inside Supabase Edge Functions
- no frontend access to service-role credentials
- no direct dependency from domain models to Supabase SDK types
- no multi-cloud abstraction beyond the small interfaces required for portability

## Follow-Up Decisions

- Select the first hosted container runtime before the deployment PR.
- Choose SQLAlchemy + Alembic, SQLModel + Alembic, or plain SQL migrations.
- Define the Supabase Auth JWT and row-level-security policy.
- Define pgmq visibility, retry, dead-letter, and idempotency behavior.
- Define private bucket layout and signed upload/download policy.
- Establish the threshold for moving queue, event, or worker workloads to AWS.
