# Frontend Workspace

## Product Direction

The frontend should be a knowledge workspace, not only a report generation app. Chat is
the main control and reasoning surface, while the center panel changes based on the
current application: knowledge overview, source inspection, deep research, report editor,
or future wiki/export workflows.

Report generation and editing remain a first-class application, but they should use the
same project knowledge, assets, graph records, and memories as chat and source ingestion.

## Primary Layout

```text
┌────────────────────────────────────────────────────────────────────┐
│ Top bar: project, active task, app mode, export/share/settings     │
├─────────────────┬──────────────────────────────────┬───────────────┤
│ Chat / Control  │ Active Knowledge App             │ Evidence      │
│                 │                                  │ Sources       │
│ follow-ups      │ structured document blocks       │ Assets        │
│ approvals       │ markdown/rich editing            │ Graph         │
│ task controls   │ source/chat/report views         │ Memory        │
│                 │                                  │ Activity      │
└─────────────────┴──────────────────────────────────┴───────────────┘
```

### Left Panel: Chat And Control

The left panel is where the user steers the agent:

- ask follow-up questions
- ask direct questions over uploaded or connected knowledge
- ask the agent to ingest, deepen, compare, summarize, or remember
- approve/edit/reject topics and outlines
- answer human-in-the-loop intervention cards
- approve or reject proposed memories
- cancel or resume tasks
- inspect compact task status

The chat panel is the command and feedback loop for the knowledge workspace. It should
work for Q&A, ingestion, memory correction, research, and report editing.

### Center: Active Knowledge App

The center panel is the main product surface. It should support multiple app modes:

- Knowledge overview: project map, recently ingested sources, open questions, memories
- Source reader: source card, original asset preview, known chunks, citations
- Chat answer view: answer, citations, follow-up actions
- Deep research view: plan, evidence coverage, findings, output draft
- Report editor: sections, citations, visual asset blocks, suggestions

The report editor is the first rich application mode.

### Report Editor

V1 should use Markdown as the canonical stored report format, but present it through a
structured editor that supports:

- headings
- paragraphs
- lists
- tables
- source excerpts
- inline citations
- generated images
- generated charts
- diagrams
- callouts
- code blocks
- section status and stale markers
- editor suggestions

Recommended editor direction:

- canonical format: Markdown plus structured frontmatter/metadata
- visual editor: Tiptap/ProseMirror or Lexical
- initial fallback: Markdown editor/preview if visual editor scope needs to shrink

Tiptap/ProseMirror is the preferred candidate because custom nodes for citations, assets,
comments, tables, and report blocks are mature and well understood.

### Right Panel: Evidence, Assets, Graph, Activity

The right panel should use tabs:

- Sources: source cards, citations, raw asset links
- Claims: extracted claims, support/contradiction state
- Graph: known relationships and retrieval result paths
- Review: unresolved entities, uncertain candidates, merge proposals, and stale citations
- Memory: user corrections, project decisions, preferences, and source quality notes
- Assets: uploaded/generated images, charts, tables, exports
- Activity: agent/subagent timeline and tool events

The user should be able to inspect why an answer or report section was produced, open the
underlying source, and insert an asset from the assets tab into the report editor when in
report mode.

## Visual Asset Blocks

Visual assets are first-class report blocks. A visual block points to an `asset_id` and
may also point to source/citation/graph records.

Examples:

```text
ImageBlock
  asset_id
  caption
  alt_text
  citation_ids
```

```text
ChartBlock
  asset_id              rendered chart image/SVG
  data_asset_id         CSV or structured data source
  chart_spec            Vega-Lite/JSON config later
  caption
  citation_ids
```

```text
TableBlock
  markdown_table
  data_asset_id
  citation_ids
```

This lets the editor display visual artifacts while preserving provenance and export
paths.

## Report Storage Strategy

V1 can store report sections as:

```text
knowledge_files(file_type = report_section)
graph_nodes(type = report_section)
graph_edges(report_section)-[:CITES]->(source/chunk/code_reference)
graph_edges(report_section)-[:USES_ASSET]->(asset/artifact)
```

The editor can maintain a structured block representation in frontmatter or metadata
while writing Markdown as the canonical content body.

Dedicated report/report_section/block tables can be added later if rich editing,
collaboration, or exports require stronger constraints.

## Export Direction

Initial exports:

- Markdown
- PDF later
- PPTX/slides later

Visual asset blocks should preserve enough metadata for export pipelines:

- source asset
- rendered asset
- caption
- citations
- chart/data config when available

## V1 Build Order

1. Shell layout: left chat/control, center active app, right tabs.
2. Project knowledge overview and source/asset panels.
3. Event timeline and task status from WebSocket.
4. Chat answer view over local/project knowledge.
5. Memory approval and memory inspection panel.
6. Markdown report editor with section list.
7. Source/citation panel.
8. Asset panel with image/chart/table insertion.
9. Suggestion/comment markers.
10. Rich block editor with custom citation and asset nodes.
