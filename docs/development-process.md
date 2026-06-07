# Development Process

## Working Model

The repo is organized around small, reviewable PRs mapped to GitHub issues. The intended
loop is:

1. Create or refine an issue.
2. Create a branch named after the issue.
3. Implement the smallest useful slice.
4. Run local checks.
5. Push and open a PR.
6. Review, adjust, and merge after CI.

## Issue Size

Issues should be feature-sized, not epic-sized. A good issue can be reviewed in one PR and
has concrete acceptance criteria. If implementation reveals multiple independent layers,
open follow-up issues instead of stretching the PR.

## First Build Sequence

1. Harness contracts and execution loop.
2. Tool protocol, registry, validation, and permission hooks.
3. API and worker runtime shell.
4. Document and web research tools.
5. Planner/topic approval and streaming writer.
6. Source/report graph, citations, and editor suggestions.

## Definition Of Done

A feature is done when:

- Its acceptance criteria are met.
- Unit tests cover the expected behavior.
- CI passes.
- Documentation or examples are updated when the public contract changes.
- Follow-up work is captured in GitHub issues.
