# Evidence-First Knowledge Graph Design

## Purpose

The knowledge graph exists to make source-backed knowledge inspectable, retrievable, and
auditable. It is not a cache of facts the system assumes are true. Every extracted claim
and semantic relationship must remain connected to the exact source evidence, extraction
process, knowledge scope, and time interval that produced it.

The graph supports chat, deep research, memory, and report editing, but those applications
must not depend on a particular graph database. Postgres is the V1 system of record. A
Neo4j or other graph projection can be added when measured multi-hop workloads justify it.

## Design Principles

1. **Evidence before inference.** A model-generated claim or edge is a candidate until it
   has source evidence and passes validation.
2. **Stable product identity.** Assets, chunks, nodes, claims, edges, and embeddings use
   stable product IDs across relational, search, vector, and graph projections.
3. **Source-relative truth.** The graph records what a source or user asserted. It does not
   collapse disagreement into one global fact.
4. **Exact provenance.** Citations resolve to structured page, section, character, line,
   table, row, or code ranges rather than an opaque range string.
5. **Typed contracts.** Node types, edge types, and payloads are validated against a
   versioned registry. `metadata` is for extensions, not core semantics.
6. **Selective retrieval.** Vector, lexical, graph, and hybrid retrieval are tools chosen
   per query. Graph traversal is not the default for every question.
7. **Progressive depth.** Sources start with cheap metadata and shallow cards, then deepen
   only when a task needs sections, claims, entities, or exhaustive coverage.
8. **Reversible evolution.** Extraction, merge, promotion, rejection, correction, and
   supersession decisions are append-only or otherwise auditable.

## Knowledge Lifecycle

```text
raw asset or connector item
  -> extracted source representation
  -> stable chunks with exact source ranges
  -> extraction candidates
  -> validation and entity resolution
  -> canonical source-relative graph
  -> lexical/vector/graph projections
  -> retrieval result set with evidence paths
  -> answer, memory, or report claim
  -> citation and feedback
  -> correction, supersession, or enrichment
```

The extraction model is not allowed to write directly into the canonical graph. It writes
candidate nodes, claims, and edges. Deterministic validation, confidence policy, entity
resolution, and optional human review decide whether each candidate is promoted.

## Identity And Projection Model

Postgres assigns the canonical UUID for every durable object. Search indexes, vector
indexes, and graph projections store that UUID as their external key.

```text
product UUID
  -> Postgres canonical record
  -> full-text document
  -> optional vector embedding(s)
  -> optional Neo4j node/edge projection
```

Projection failures must not change the canonical record. Every projection tracks the
source content hash, schema version, embedding/extraction version, and last successful
sync so stale projections can be detected and rebuilt.

## Core Graph Semantics

Initial node types:

- `source`: an uploaded, fetched, or connector-owned source
- `chunk`: an exact range within a source representation
- `entity`: a canonical person, organization, place, product, concept, or code symbol
- `claim`: a source-relative proposition, not an assumed global fact
- `topic`: a research or knowledge topic
- `report_section`: a section in an application output
- `artifact`: an uploaded or generated visual, table, chart, code, or export

Initial edge types:

- `HAS_CHUNK`
- `MENTIONS`
- `ASSERTS`
- `SUPPORTED_BY`
- `CONTRADICTED_BY`
- `ABOUT`
- `SAME_AS_CANDIDATE`
- `SUPERSEDES`
- `CITES`
- `USES_ASSET`
- `DERIVED_FROM`
- `DEPENDS_ON`

Claims are the center of the evidence model:

```text
Source -> HAS_CHUNK -> Chunk
Chunk  -> ASSERTS -> Claim
Claim  -> ABOUT -> Entity/Topic
Claim  -> SUPPORTED_BY -> Chunk
Claim  -> CONTRADICTED_BY -> Chunk/Claim
Claim  -> SUPERSEDES -> Claim
ReportSection -> CITES -> Chunk/Claim
```

`SUPPORTED_BY` means the linked evidence entails or directly supports the claim.
`CONTRADICTED_BY` preserves disagreement. Neither edge makes an automatic final truth
judgment.

## Structured Provenance

Each chunk has a structured range appropriate to its source type:

```text
page_start / page_end
section_path
char_start / char_end
line_start / line_end
bounding_boxes
table_id / row_start / row_end / column_start / column_end
sheet_name / cell_range
repository / commit_sha / file_path / symbol / code_line_start / code_line_end
external_permalink / external_item_id / external_revision
```

The original asset checksum and the extracted representation checksum are stored with the
range. A citation resolver must be able to open the source representation and reproduce
the cited text. If it cannot, the citation is stale or invalid.

Every extracted candidate records:

- source chunk IDs
- extraction method (`deterministic`, `parser`, `model`, `user`)
- parser/model and version
- prompt or extraction policy version
- input content hash
- confidence and validation status
- creation run and trace IDs

## Candidate Validation And Promotion

Candidates move through explicit states:

```text
extracted -> validating -> accepted
                        -> rejected
                        -> needs_review
accepted  -> superseded / corrected / archived
```

Minimum automatic promotion requirements:

1. Required typed fields validate.
2. At least one source chunk resolves successfully.
3. The supporting text still matches the recorded content hash.
4. The candidate does not violate scope or connector permissions.
5. Entity resolution completes or leaves an explicit unresolved entity.
6. The relation is allowed by the node/edge type registry.

Confidence alone must not promote unsupported knowledge. High-impact memories, user
corrections, sensitive claims, and destructive merges can require user approval.

## Entity Resolution

Entity resolution is explicit and reversible. It uses, in decreasing strength:

1. provider or domain external ID
2. deterministic domain key such as repository + commit + symbol
3. normalized exact identifier
4. alias table
5. constrained similarity candidate
6. human or agent-assisted review

Similarity creates a merge candidate; it does not silently merge entities. Merge records
preserve the survivor, merged entity, reason, evidence, actor, and timestamp. Splitting a
bad merge must be possible.

## Versioning, Time, And Disagreement

Nodes, claims, and edges support:

- transaction time: when the system learned or changed the record
- valid time: when the source says the assertion was true
- source revision: which external or file version produced it
- supersession: which newer record replaces it
- retraction or correction status

Conflicting claims remain separate and retain their evidence:

```text
Claim A: "Project ships in June"  <- Source revision 1
Claim B: "Project ships in July"  <- Source revision 2
Claim B -> SUPERSEDES -> Claim A
```

The answer layer decides how to explain the conflict using recency, authority, explicit
correction, and user policy. The graph does not erase the history.

## Embedding Strategy

Embeddings are projections, not canonical knowledge. Supported targets can include:

- chunks
- entity names and descriptions
- claims
- relation triplets
- source or topic summaries

Each embedding records its target ID, target field, content hash, model, dimensions, and
created time. V1 should embed chunks first. Claim, entity, and triplet embeddings are
enabled only when evaluation demonstrates better retrieval for a defined query class.

## Retrieval Routing

The query planner chooses the cheapest retrieval mode likely to satisfy the request:

```text
exact phrase or identifier  -> lexical/full-text
semantic fact lookup        -> vector chunks
entity lookup               -> entity index + supporting chunks
relationship question       -> graph traversal + supporting chunks
multi-hop question          -> hybrid vector seed + bounded graph paths
report verification         -> claim/evidence/report graph
```

All modes return the same `RetrievalResultSet` contract:

```text
query_id
knowledge_scope_ids
strategy and strategy_version
ranked result IDs and scores
graph paths, when used
supporting chunk IDs and exact ranges
source and projection versions
filters and permission decisions
timings, token cost, and trace ID
```

The result contract distinguishes retrieval score from evidence status. Semantic
similarity does not mean a source supports a claim.

## Progressive Ingestion And Enrichment

```text
0 discovered
1 metadata_only
2 shallow_card
3 section_indexed
4 topic_deepened
5 claims_extracted
6 exhaustively_indexed
```

Enrichment operates on existing canonical records and candidates without re-ingesting the
asset unnecessarily. Initial enrichment capabilities:

- deepen selected source ranges
- propose entity aliases and merge candidates
- extract or re-extract claims under a new policy version
- identify supporting and contradicting evidence
- detect stale citations after a source update
- rebuild selected embeddings or graph projections

## Evaluation Requirements

Graph changes are evaluated against a versioned fixture corpus. Minimum metrics:

- source/chunk provenance accuracy
- entity precision, recall, and duplicate rate
- relation and claim extraction precision/recall
- unsupported canonical claim rate
- entity merge precision and reversible-merge correctness
- stale projection and deletion correctness
- retrieval recall/precision by query class
- citation entailment and range accuracy
- contradiction and supersession handling
- latency, token cost, and ingestion cost

Every graph retrieval experiment compares at least lexical/vector chunk retrieval against
the graph or hybrid strategy. Graph retrieval is adopted for a query class only when it
improves quality enough to justify its latency and operational cost.

## V1 Boundary

V1 implements:

- Postgres canonical graph repository
- stable product IDs
- sources, structured chunks, entities, claims, and evidence edges
- extraction candidate and promotion workflow
- exact source-range citation resolution
- deterministic external-ID deduplication and alias candidates
- full-text and chunk-vector retrieval
- bounded one- and two-hop graph traversal in Postgres
- retrieval result set traces
- graph ingestion and retrieval evaluation fixtures

V1 defers:

- mandatory Neo4j
- automatic similarity-based entity merges
- unrestricted model-generated relation types
- embedding every graph object
- global ontology induction
- long autonomous enrichment loops
- graph traversal for every query

## Related Documents

- [Architecture](architecture.md)
- [Data Model And ERD](data-model.md)
- [DeepAgents System Design](deepagents-system-design.md)
- [Source Connectors](source-connectors.md)
- [Frontend Workspace](frontend-workspace.md)
