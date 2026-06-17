# Harness Strategy

## Decision

V1 uses LangChain DeepAgents as the agent harness framework.

DeepAgents already provides the capabilities we need for the agent engine: planning,
tools, context management, subagents, event streaming, permissions, filesystem backends,
memory, and human-in-the-loop control. We should integrate those capabilities instead of
rebuilding an agent runtime inside this repo.

## Our Boundary

The application owns product contracts and persistence:

- `ResearchRun`
- `ResearchTask`
- `ResearchEvent`
- research tool definitions
- source and report graph models
- citation models
- API, worker, and WebSocket integration

DeepAgents owns agent execution:

- model/tool loop
- planning behavior
- context management
- subagent orchestration
- SDK-native streaming
- SDK-native interruption and approval flow

`packages/harness_core` is the adapter between those two worlds.

## M1 Scope

M1 should prove the integration path:

1. Define product-level run, task, and event contracts.
2. Define a small adapter interface for starting a DeepAgents-backed run.
3. Map DeepAgents stream events into product events.
4. Expose one simple tool through DeepAgents.
5. Run deterministic tests with fake adapters and one SDK-backed smoke path.

M1 should not implement a custom agent loop, custom planner engine, or custom tool
runtime unless DeepAgents cannot support a required product contract.

## Adapter Shape

```text
ResearchTask
  -> HarnessAdapter.start(task)
    -> DeepAgents agent stream
      -> ResearchEvent
```

The rest of the application consumes `ResearchEvent`, not DeepAgents-specific stream
objects.

## Tool Strategy

Research tools should be ordinary Python functions or LangChain-compatible tools that can
be passed into DeepAgents. Our code should define product metadata, validation,
permissions, and structured results around those tools where needed.

## Open Questions

- Which model provider should be the first default for local development?
- Which DeepAgents filesystem backend should we use first?
- How much of DeepAgents permissions should we expose directly versus wrapping in our own
  product policy?
- Which DeepAgents stream projections should map to persisted product events?
