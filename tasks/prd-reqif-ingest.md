# PRD: Deterministic Document Distillation -> ReqIF

## Status

- Branch: `feature/aemo-pdf-reqif-plan`
- Current repo capability: parse and normalize existing ReqIF XML only
- Missing capability: ingest PDF, DOCX, Markdown, and XLSX artifacts into a derived ReqIF baseline

## Problem

The repo evaluates existing ReqIF baselines, but it does not create them from source artifacts.
That leaves a gap between policy/toolkit documents and the deterministic OPA/SARIF path.

Requirement extraction and distillation are subjective. The first pass MUST therefore be
deterministic, traceable, and explicit about provenance, while leaving design hooks for optional
LLM-assisted quality evaluation and document-specific mapping skills.

## Design Constraints

- First-pass distillation MUST be deterministic.
- LLM usage MUST be optional and gated after deterministic extraction.
- XLSX MUST be a first-class source format, not an afterthought.
- Source artifacts MUST be treated as immutable evidence with referenceable hashes.
- Provenance MUST preserve format-specific anchors:
  - PDF: page, paragraph, span, semantic section identifier
  - DOCX: heading path, paragraph, table cell, semantic identifier
  - Markdown: heading path, paragraph, list item, semantic identifier
  - XLSX: workbook, sheet, row, column, range, mapped semantic header identifier
- Distillation SHOULD flow through an intermediate representation before ReqIF emission.
- Capability MUST be surfaced as standalone tooling and exposed to agents via MCP tools.
- Skills SHOULD be layered:
  - generic by file type
  - document-family specific
  - document-instance specific, e.g. AESCSF
- ReqIF MUST remain a derived artifact from the distillation process.

## Current Findings

### Repo

- `reqif_mcp.server.reqif_parse` accepts only base64 ReqIF XML input.
- `reqif_mcp.reqif_parser.parse_reqif_xml` parses only XML or XML file paths.
- No source adapter exists for PDF, DOCX, Markdown, or XLSX.
- No ReqIF emission path exists.
- No artifact hashing, provenance IR, or baseline diff pipeline exists for source documents.
- No ingest-oriented MCP tool surface exists yet.

### AEMO Fixtures

- `evidence_store/toolkits/aemo/aescsf-2025-overview.pdf`
- `The AESCSF v2 Core.xlsx`
- `V2 AESCSF Toolkit Version V1-1.xlsx`

## Target Architecture

### 1. Artifact Intake

Standalone tool registers a source artifact and produces immutable metadata:

- `artifact_id`
- `sha256`
- `source_uri`
- `media_type`
- `filename`
- `ingested_at`
- `document_profile`

This stage does not interpret requirements. It only establishes provenance.

### 2. Structural Extraction

Use OSS extractors to produce a canonical document graph:

- `artifact/1` -> immutable artifact metadata
- `document_graph/1` -> sections, paragraphs, tables, cells, anchors, semantic IDs

Preferred stack:

- `docling` for PDF, DOCX, Markdown, and XLSX ingestion
- `openpyxl` only where XLSX-specific cell metadata or formulas exceed Docling coverage

### 3. Deterministic Distillation

Convert `document_graph/1` into `requirement_candidate/1` records using deterministic rules:

- heading and section heuristics
- workbook header mapping tables
- pattern-driven extraction for shall/must/should semantics
- per-document profile rules, e.g. AESCSF workbook mapping

Output MUST include:

- candidate ID
- requirement text
- source anchors
- extraction rationale
- confidence source
- subtype hints
- provenance back to artifact hash

### 4. Optional LLM Quality Gates

This stage is disabled by default. It does not create requirements from scratch.
It evaluates, ranks, or proposes remappings for deterministic outputs.

Adapter boundary:

- `quality_eval/1` interface
- providers MAY include Microsoft Foundry, DSPy, or LangChain
- agent skills MAY supply document-specific prompts and evaluation rules

### 5. ReqIF Emission

Convert `requirement_candidate/1` into ReqIF XML via a maintained OSS emitter library.
ReqIF is published only after deterministic validation passes.

### 6. Baseline Diff

Compare normalized requirement records across runs:

- added requirements
- removed requirements
- changed text
- changed provenance
- changed subtype/rubric mapping

This produces a versioned diff report for review and later OPA integration.

## Intermediate Representations

### `artifact/1`

Immutable source artifact record with hash and metadata.

### `document_graph/1`

Canonical structural graph independent of ReqIF:

- nodes: section, paragraph, table, row, cell, list item
- edges: contains, follows, derived_from, mapped_by
- anchors: page, heading path, sheet name, cell range

### `requirement_candidate/1`

Deterministic distillation output:

- canonical candidate text
- candidate type/subtype
- evidence anchors
- rule ID used for extraction
- semantic identifier for source structure

### `quality_eval/1`

Optional post-processing evaluation output:

- accepted/rejected
- issues
- proposed header remap
- coverage gaps

## MCP Tool Surface

The standalone distillation tool SHOULD expose MCP tools so agents can operate on artifacts
without direct code coupling.

Proposed tools:

- `artifact_register(path|uri) -> artifact/1`
- `artifact_hash(artifact_id) -> sha256`
- `document_extract(artifact_id, profile?) -> document_graph/1`
- `document_distill(artifact_id, profile, deterministic=true) -> requirement_candidate[]`
- `document_quality_eval(candidate_set_id, evaluator?) -> quality_eval/1`
- `reqif_emit(candidate_set_id, baseline_meta) -> reqif_artifact`
- `reqif_diff(old_reqif, new_reqif) -> diff_report`
- `skill_suggest(artifact_id) -> skill list`

## Skills Model

### Generic Skills

- `pdf.distill`
- `docx.distill`
- `markdown.distill`
- `xlsx.distill`

### Document-Family Skills

- `cyber-framework.distill`
- `controls-matrix.xlsx-map`
- `policy-overview.pdf-map`

### Document-Specific Skills

- `aescsf.distill`
- `aescsf.xlsx-header-map`
- `aescsf.pdf-structure-map`

Skill outputs are configuration and mapping inputs to deterministic extraction. Optional LLM
quality evaluators MAY also use these skills, but MUST not be required for the first pass.

## Open-Source Tooling Strategy

### MUST Use

- `docling` for source extraction
- existing repo ReqIF parser/normalizer for round-trip validation
- `uv` for dependency management
- `ruff`, `mypy`, `pytest` for quality gates

### SHOULD Evaluate

- maintained ReqIF emitter library before writing custom XML
- `openpyxl` for XLSX edge cases
- `dspy` for evaluator orchestration
- `langchain` only as an adapter layer, not as the core data model
- Microsoft Foundry adapters only behind the optional evaluator boundary

### MUST Avoid

- direct PDF-to-ReqIF conversion without an intermediate representation
- LLM-first extraction
- custom XML generation if a maintained ReqIF emitter is viable
- format-specific logic embedded directly into MCP handlers

## Delivery Plan

### Phase 1: Foundation

- Add test fixtures for the AEMO PDF and both XLSX files.
- Define `artifact/1`, `document_graph/1`, and `requirement_candidate/1` schemas.
- Add artifact hashing and provenance utilities.

### Phase 2: Deterministic Extraction

- Integrate Docling ingestion for PDF, DOCX, Markdown, and XLSX.
- Add XLSX-first header mapping support.
- Build deterministic extraction rules for AESCSF fixtures.

### Phase 3: ReqIF Derivation

- Add ReqIF emission from requirement candidates.
- Round-trip emitted ReqIF through the existing parser and normalizer.
- Add versioned diffing between source runs.

### Phase 4: Agent Surface

- Expose standalone capability via MCP tools.
- Add generic file-type skills and AESCSF-specific skills.
- Add optional evaluator interface for Foundry, DSPy, or LangChain adapters.

## Acceptance Criteria

- A PDF artifact can be registered, hashed, extracted, distilled, and emitted as ReqIF.
- An XLSX artifact can be registered, hashed, extracted, header-mapped, distilled, and emitted as ReqIF.
- Every derived requirement preserves provenance to its source artifact and format-specific anchor.
- ReqIF output round-trips through the current parser/normalizer without schema failure.
- Diff reports show changes between successive source artifact versions.
- MCP tools expose the standalone capability to agents.
- Optional LLM evaluator hooks exist but are disabled by default.

## Testing Strategy

- Unit tests for hashing, provenance anchors, header mapping, and deterministic rules
- Fixture tests for AESCSF PDF and XLSX artifacts
- Round-trip tests: candidate set -> ReqIF -> parser -> normalized record
- Regression tests for baseline diffing
- Integration tests for MCP tool flows

## Non-Goals

- Replacing ReqIF as the evaluation interchange format
- Making LLM evaluation mandatory
- Combining extraction, distillation, and policy evaluation into a single opaque step
