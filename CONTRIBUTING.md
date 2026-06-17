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
- Web placeholder tests: `npm test` in `apps/web`

As the frontend becomes real, web CI should grow to install dependencies, run type checks,
lint, unit tests, and eventually Playwright smoke tests.

## Review Cadence

We will keep PRs small enough that review stays useful. For larger work, split into:

1. contract/model PR
2. runtime/service PR
3. behavior/tool PR
4. UI integration PR

That keeps the system moving without hiding too much design in a single diff.
