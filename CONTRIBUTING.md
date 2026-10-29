# Contributing

This repo is being built issue-by-issue. Each meaningful feature should have a GitHub
issue, a focused branch, a pull request, and passing CI.

## Branches

Use short issue-linked branch names:

```text
issue-7-repo-process
issue-12-tool-permissions
issue-9-planner-topic-proposals
```

## Commits

Commit at reviewable checkpoints. Prefer commits that explain the product step:

```text
Add tool permission policy hooks
Wire run creation endpoint
Define citation model
```

## Pull Requests

Every PR should:

- Link its issue with `Closes #<number>` when it fully completes the issue.
- Include a short implementation summary.
- List the checks run locally.
- Call out follow-up issues instead of widening scope.

## CI

CI currently runs:

- Python lint: `ruff check .`
- Python tests: `pytest`
- Web lint: `npm run lint` in `apps/web`
- Web type checking: `npm run typecheck` in `apps/web`
- Web unit tests: `npm test` in `apps/web`
- Web production build: `npm run build` in `apps/web`
- Docker Compose validation and service image builds

Playwright smoke tests will be added once the API-backed knowledge workflow is wired.

## Review Cadence

We will keep PRs small enough that review stays useful. For larger work, split into:

1. contract/model PR
2. runtime/service PR
3. behavior/tool PR
4. UI integration PR

That keeps the system moving without hiding too much design in a single diff.
