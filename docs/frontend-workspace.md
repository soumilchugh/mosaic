# Frontend Workspace

## Product Direction

The frontend should be a report generation and editing workspace, not a chat-first app.
Chat is a control surface on the side. The generated report and evidence workspace are
the primary experience.

## Primary Layout

```text
┌────────────────────────────────────────────────────────────────────┐
│ Top bar: project, run status, export, share, settings              │
├─────────────────┬──────────────────────────────────┬───────────────┤
│ Chat / Control  │ Report Editor                    │ Evidence      │
│                 │                                  │ Sources       │
│ follow-ups      │ structured document blocks       │ Assets        │
│ approvals       │ markdown/rich editing            │ Graph         │
│ run controls    │ citations and visuals            │ Activity      │
└─────────────────┴──────────────────────────────────┴───────────────┘
```

### Left Panel: Chat And Control

The left panel is where the user steers the agent:

- ask follow-up questions
- approve/edit/reject topics and outlines
- answer human-in-the-loop intervention cards
- cancel or resume runs
- inspect compact run status

The chat panel should not be the center of gravity. It is the command and feedback loop
for the report workspace.

### Center: Report Editor

The center panel is the main product surface.

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
- Assets: uploaded/generated images, charts, tables, exports
- Activity: agent/subagent timeline and tool events

The user should be able to insert an asset from the assets tab into the report editor.

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

1. Shell layout: left chat/control, center report, right tabs.
2. Event timeline and run status from WebSocket.
3. Markdown report editor with section list.
4. Source/citation panel.
5. Asset panel with image/chart/table insertion.
6. Suggestion/comment markers.
7. Rich block editor with custom citation and asset nodes.
