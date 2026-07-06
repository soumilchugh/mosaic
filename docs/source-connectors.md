# Source Connectors

## Purpose

Source connectors bring external data into the same knowledge and memory platform as
local uploads. A connector should not create a separate product path. It should produce
assets, knowledge files, graph records, chunks, citations, and sometimes memory
candidates.

The goal is to support many source types while keeping one agent-facing knowledge model.

## Connector Families

### Local Sources

Examples:

- PDFs
- Word documents
- Markdown/text files
- spreadsheets and CSVs
- images
- code folders or archives
- exported chat/message archives

Use local sources first because they exercise the same ingestion path without OAuth,
remote permissions, or sync complexity.

### Web Sources

Examples:

- single URLs
- crawled sites
- RSS feeds
- documentation sites
- saved browser pages

Web sources need fetch timestamps, canonical URLs, content hashes, and snapshots so later
answers can cite what the agent actually saw.

### Team Communication

Examples:

- Slack channels
- Slack threads
- Slack files
- Microsoft Teams later
- Discord later

These sources are useful for decisions, context, action items, and "what did we decide?"
questions. Threads should preserve authors, timestamps, channel IDs, thread IDs, message
permalinks, reactions when useful, and attached files.

### Work Management

Examples:

- Linear issues
- Jira tickets
- GitHub issues
- GitHub pull requests

These sources are useful for project history, decision trails, open questions, ownership,
and status summaries.

### Code And Engineering

Examples:

- GitHub repositories
- GitLab repositories later
- commits
- pull requests
- code files
- symbols and dependency graphs

Code sources should preserve repository, branch, commit SHA, path, line ranges, symbols,
and file hashes.

### Knowledge Apps

Examples:

- Notion
- Google Drive
- Confluence
- Dropbox Paper later

These sources are often semi-structured. They should preserve document IDs, titles,
owners, permissions, folder/page hierarchy, update times, and export snapshots.

### Email And Calendar

Examples:

- Gmail
- Outlook
- calendar events
- meeting notes

These should come later because they are sensitive and require careful permission,
privacy, and memory policies.

### Databases And APIs

Examples:

- Postgres read replicas
- analytics warehouses
- CRM APIs
- internal product APIs

These should be treated as structured source connectors with schema metadata, query
permissions, result snapshots, and audit logs.

## Standard Connector Output

Every connector should map external source data into the same internal objects:

```text
external source item
  -> source_connector
  -> source_sync_run
  -> asset
  -> knowledge_file
  -> graph_chunk / extraction_candidate
  -> validated graph_node / graph_edge
  -> optional memory_candidate
```

The connector should preserve:

- external source ID
- provider name
- source URL or permalink
- author/owner when available
- created and updated timestamps
- permissions/visibility
- content hash
- sync cursor
- source metadata needed for citations

Connector content does not write semantic claims or relationships directly into the
canonical graph. It creates source records, structured chunks, and extraction candidates
that follow the validation and promotion rules in
[knowledge-graph-design.md](knowledge-graph-design.md).

## Ingestion Levels

Connectors should support progressive ingestion:

1. **Metadata only**
   Store source ID, title, author, timestamps, URL, and permissions.

2. **Shallow card**
   Create a short agent-readable summary, topics, entities, and structure hints.

3. **Indexed chunks**
   Store chunk/page/message/thread ranges that can route the agent to relevant content.

4. **Deep extraction**
   Extract claims, facts, decisions, tables, code symbols, citations, and relationships.

5. **Memory candidates**
   Propose durable memories when a source contains decisions, corrections, preferences,
   source quality notes, or reusable project knowledge.

The system should default to shallow ingestion and deepen only when a user question,
agent task, or connector policy requires it.

## Permission Model

Connector permissions matter because the knowledge base can mix sources.

V1 should record permissions even if enforcement is simple:

- who connected the source
- which project or knowledge scope owns it
- source visibility
- external ACL snapshot when available
- whether the agent can read raw content
- whether the agent can write back to the source
- whether memory extraction is allowed

Write-back should be disabled by default. It should require explicit approval.

## First Connector Recommendation

Recommended build order:

1. **Local uploads**
   Lowest integration risk and validates assets, ingestion, graph, citations, and chat.

2. **Web URLs**
   Useful for research and citations without OAuth complexity.

3. **GitHub**
   Strong fit for code search, issues, PRs, and engineering knowledge.

4. **Slack**
   High product value for team memory and decisions, but higher permission and noise
   complexity.

5. **Google Drive or Notion**
   Good document sources, but each has hierarchy, permissions, and sync complexity.

Slack is strategically important, but it may be better after the memory policy and
connector permission model are stable.

## Agent Behavior

When answering a question, the agent should:

1. Search conversation context and relevant memories.
2. Search project and global knowledge scopes.
3. Search connector-produced knowledge files and graph records.
4. Read targeted source chunks or raw assets only when needed.
5. Deepen the source if the answer needs more detail.
6. Save useful findings, citations, and memory candidates.

The agent should not blindly trust all connector data. It should prefer recent,
permission-valid, source-linked, and user-approved knowledge when conflicts exist.

## Open Decisions

- Which connector should be first after local uploads and web URLs?
- Do connector syncs run manually, on schedule, or both?
- Should Slack decisions become memory candidates automatically?
- How should external permissions affect user-global knowledge?
- Should connector data be copied into our object storage, referenced in place, or both?
- Which connectors need write-back support, if any?
