# PRD: ReqIF→OPA→SARIF Compliance Gate System (MVP)

## Introduction

Build a research prototype compliance gate system that transforms requirements (ReqIF format) into deterministic policy evaluations (OPA) with standardized reporting (SARIF). The system enables CI/CD pipelines to verify that code changes meet policy requirements through automated, auditable gates. This MVP focuses on proving the core concept with all components working end-to-end, prioritizing the ReqIF data model and parsing foundation first.

## Goals

- Parse and validate ReqIF 1.2 XML documents into normalized requirement records
- Establish data contracts for requirement records, agent facts, and OPA evaluation schemas
- Integrate OPA for deterministic policy evaluation against structured facts
- Generate SARIF v2.1.0 compliant reports mapping requirements to results
- Provide a FastMCP 3.0 server exposing ReqIF tools and resources via HTTP/STDIO
- Create an agent runner contract for fact extraction from artifacts
- Support flexible deployment (local dev, CI/CD pipelines, containerized)
- Maintain audit trail through OPA decision logs and evidence storage
- Prove the concept with end-to-end integration tests

## User Stories

### Phase 1: Foundation - ReqIF Data Model & Parsing (PRIORITY)

### US-001: Define requirement record schema
**Description:** As a system architect, I need a canonical requirement record schema so that all components share a consistent data model.

**Acceptance Criteria:**
- [ ] JSON schema defined for `reqif-mcp/1` with fields: uid, key, subtypes[], status, policy_baseline, rubrics[], text, attrs
- [ ] Schema includes enums for status (active/obsolete/draft)
- [ ] Schema includes policy_baseline structure with id, version, hash
- [ ] Schema includes rubrics array with engine, bundle, package, rule fields
- [ ] Schema documentation generated (JSON Schema or equivalent)
- [ ] Validation function can check conformance to schema

### US-002: Parse ReqIF 1.2 XML documents
**Description:** As a compliance officer, I want to parse ReqIF XML documents so that requirements can be ingested into the system.

**Acceptance Criteria:**
- [ ] Parser accepts ReqIF 1.2 XML input (as base64 or file path)
- [ ] Parser extracts core elements: SpecObjects, SpecTypes, AttributeDefinitions, AttributeValues
- [ ] Parser handles well-formed XML successfully
- [ ] Parser detects and reports malformed XML with clear error messages
- [ ] Parser validates ReqIF structure against ReqIF 1.2 schema
- [ ] Returns parsed handle or structured error report

### US-003: Normalize ReqIF to requirement records
**Description:** As a developer, I need ReqIF data normalized into requirement records so that downstream components can consume a consistent format.

**Acceptance Criteria:**
- [ ] Normalization maps ReqIF SpecObject → requirement record
- [ ] Extracts uid from ReqIF identifier or generates stable UID
- [ ] Maps attributes to normalized fields (key, text, subtypes, status)
- [ ] Extracts policy_baseline and rubric references from custom attributes
- [ ] Handles missing optional fields gracefully with sensible defaults
- [ ] Produces valid `reqif-mcp/1` JSON for each requirement
- [ ] Creates in-memory index by uid, key, and subtypes

### US-004: Validate requirement record integrity
**Description:** As a system administrator, I want validation of requirement records so that invalid data is caught early.

**Acceptance Criteria:**
- [ ] Validation checks all required fields are present
- [ ] Validation checks uid uniqueness within a baseline
- [ ] Validation checks policy_baseline references are resolvable
- [ ] Validation checks rubric references have required fields (engine, bundle, package, rule)
- [ ] Returns structured validation report with errors and warnings
- [ ] Supports two modes: basic (structure only) and strict (referential integrity)

### US-005: FastMCP 3.0 server scaffold with ReqIF tools
**Description:** As a CI/CD engineer, I want a FastMCP server exposing ReqIF operations so that pipelines can interact via MCP protocol.

**Acceptance Criteria:**
- [ ] FastMCP 3.0 server initialized with HTTP transport support
- [ ] Server supports STDIO transport for local development
- [ ] Tool `reqif.parse` accepts xml_b64 parameter and returns handle
- [ ] Tool `reqif.validate` accepts handle and mode (basic/strict) and returns report
- [ ] Tool `reqif.query` accepts filters (baseline, subtypes[], status, limit, offset) and returns requirement records
- [ ] Server handles errors gracefully and returns structured error responses
- [ ] Server can be started/stopped via command line

### US-006: Query requirements by subtype and baseline
**Description:** As a CI pipeline, I want to query requirements filtered by subtype and baseline so that only relevant requirements are evaluated.

**Acceptance Criteria:**
- [ ] Query supports filtering by subtypes[] (AND/OR logic configurable)
- [ ] Query supports filtering by baseline id
- [ ] Query supports filtering by status (active/obsolete/draft)
- [ ] Query supports pagination via limit and offset
- [ ] Query returns array of requirement records matching filters
- [ ] Empty result set returns empty array (not error)
- [ ] Query results are deterministic (consistent ordering)

### Phase 2: Policy Evaluation - OPA Integration

### US-007: Define agent facts schema
**Description:** As an agent developer, I need a standard schema for facts so that OPA policies can consume structured data consistently.

**Acceptance Criteria:**
- [ ] JSON schema defined for `facts/1` with fields: target, facts, evidence[], agent
- [ ] Schema includes target structure (repo, commit, build)
- [ ] Schema includes evidence array with type, uri, startLine, endLine, hash fields
- [ ] Schema includes agent metadata (name, version, rubric_hint)
- [ ] Facts object is flexible (accepts arbitrary fact keys)
- [ ] Validation function checks conformance to schema

### US-008: Define OPA evaluation contract
**Description:** As a policy author, I need a clear contract for OPA input/output so that policies return consistent decision structures.

**Acceptance Criteria:**
- [ ] OPA input schema defined: {requirement, facts, context}
- [ ] OPA output schema defined with status enum (pass/fail/conditional_pass/inconclusive/not_applicable/blocked/waived)
- [ ] Output includes score (0.0-1.0), confidence (0.0-1.0)
- [ ] Output includes criteria array with id, status, weight, message, evidence indices
- [ ] Output includes reasons[] (human-readable strings)
- [ ] Output includes policy provenance (bundle, revision, hash)
- [ ] Schema documentation available for policy authors

### US-009: Create OPA bundle template
**Description:** As a policy author, I need an OPA bundle template so that I can create rubric policies following the standard structure.

**Acceptance Criteria:**
- [ ] Bundle directory structure created: policy/, data/, .manifest
- [ ] Template includes example rubric policy for one subtype (e.g., CYBER)
- [ ] Template shows how to access input.requirement and input.facts
- [ ] Template demonstrates returning full decision object with criteria
- [ ] Template includes data/*.json for lookup tables/thresholds
- [ ] Bundle metadata includes version and hash computation
- [ ] Documentation explains how to author new rubric packages

### US-010: Integrate OPA evaluation engine
**Description:** As a CI pipeline, I want to evaluate requirements against facts using OPA so that deterministic compliance decisions are made.

**Acceptance Criteria:**
- [ ] OPA evaluator component can load OPA bundles from filesystem
- [ ] Evaluator composes OPA input from requirement + facts + context
- [ ] Evaluator invokes OPA (local binary or REST API)
- [ ] Evaluator parses OPA decision output into structured object
- [ ] Evaluator validates OPA output conforms to expected schema
- [ ] Returns decision object or structured error if evaluation fails
- [ ] Supports configurable OPA bundle path and endpoint

### US-011: Enable OPA decision logging
**Description:** As an auditor, I want OPA decision logs captured so that every evaluation is auditable.

**Acceptance Criteria:**
- [ ] OPA decision logging enabled in configuration
- [ ] Each evaluation produces a decision log entry
- [ ] Decision log includes input (requirement + facts), output (decision), timestamp, policy version
- [ ] Decision logs written to append-only log file (JSONL format)
- [ ] Decision logs include unique evaluation id for traceability
- [ ] Log rotation or archival strategy documented (even if not implemented in MVP)

### Phase 3: Agent Contract & Facts

### US-012: Define agent runner interface
**Description:** As an agent developer, I need a clear interface contract so that agents can be plugged into the system consistently.

**Acceptance Criteria:**
- [ ] Agent runner interface defined: run_agent(subtype, artifacts_path, requirement_context) -> facts
- [ ] Interface specifies input parameters: subtype string, artifacts directory path, requirement subset
- [ ] Interface specifies output: facts object conforming to `facts/1` schema
- [ ] Interface documented with examples
- [ ] Error handling contract defined (return error object, not throw)
- [ ] Agent runner can be invoked via CLI or programmatically

### US-013: Create stub agent for testing
**Description:** As a system tester, I need a stub agent that produces synthetic facts so that integration tests can run without real agents.

**Acceptance Criteria:**
- [ ] Stub agent accepts subtype parameter
- [ ] Stub agent generates synthetic facts appropriate for subtype (e.g., CYBER: uses_crypto_library=true)
- [ ] Stub agent generates synthetic evidence pointers (code_span, artifact)
- [ ] Stub agent returns valid `facts/1` JSON
- [ ] Stub agent includes agent metadata (name, version)
- [ ] Stub agent can be run standalone for testing

### Phase 4: SARIF Reporting

### US-014: Define SARIF mapping rules
**Description:** As a compliance officer, I need clear mapping rules from OPA decisions to SARIF so that reports are consistent and standard-compliant.

**Acceptance Criteria:**
- [ ] Mapping documented: OPA status → SARIF result.level
- [ ] pass → omit result (or note if included)
- [ ] fail → error
- [ ] conditional_pass → warning
- [ ] inconclusive/blocked → warning with property triage=needed
- [ ] not_applicable → omit result
- [ ] Requirement uid/key → SARIF rule.id (stable)
- [ ] Evidence pointers → SARIF result.locations[]
- [ ] OPA criteria → SARIF result.message (reasons)
- [ ] Property bag includes: requirement_uid, requirement_key, subtypes[], policy_baseline.version, opa.policy.hash, agent.version

### US-015: Implement SARIF producer
**Description:** As a CI pipeline, I want SARIF reports generated from OPA decisions so that results can be ingested by standard tooling.

**Acceptance Criteria:**
- [ ] SARIF producer accepts OPA decision + requirement + facts as input
- [ ] Producer generates SARIF run object with tool.driver.name = bundle ID
- [ ] Producer creates SARIF rule for each requirement evaluated
- [ ] Producer creates SARIF result for each failing/warning criterion
- [ ] Producer maps OPA status to SARIF result.level per normative rules
- [ ] Producer includes locations when evidence has code spans
- [ ] Producer writes SARIF JSON to file or returns as object
- [ ] Output is valid SARIF v2.1.0 (can be validated with SARIF schema)

### US-016: Validate SARIF conformance
**Description:** As a quality engineer, I want SARIF output validated against the official schema so that reports are guaranteed interoperable.

**Acceptance Criteria:**
- [ ] SARIF validator integrated (use OSS SARIF schema validator)
- [ ] Validator checks conformance to SARIF v2.1.0 JSON schema
- [ ] Validator runs automatically in tests
- [ ] Validator reports specific schema violations with paths
- [ ] All generated SARIF files pass validation
- [ ] CI fails if SARIF validation fails

### Phase 5: Evidence & Traceability

### US-017: Implement verification event storage
**Description:** As a compliance officer, I need verification events recorded so that requirement evaluations are traceable.

**Acceptance Criteria:**
- [ ] Verification event schema defined: requirement_uid, target (commit/build), decision, timestamp, sarif_ref
- [ ] Tool `reqif.write_verification` accepts event object and writes to store
- [ ] Events stored in append-only JSONL log
- [ ] Each event includes unique event id
- [ ] Events link requirement → target → decision → SARIF artifact
- [ ] Query interface can retrieve events by requirement_uid or target

### US-018: Create evidence store structure
**Description:** As a data analyst, I need an evidence store with clear structure so that evaluation history can be queried and analyzed.

**Acceptance Criteria:**
- [ ] Evidence store directory created with subdirectories: events/, sarif/, decision_logs/
- [ ] events/ contains JSONL append-only log of verification events
- [ ] sarif/ contains SARIF artifacts named by evaluation id
- [ ] decision_logs/ contains OPA decision logs
- [ ] Store supports concurrent writes (basic file locking or unique file names)
- [ ] Documentation explains store layout and query patterns

### US-019: Export requirement sets for agents
**Description:** As an agent runner, I need to export requirement subsets in portable formats so that agents can process requirements efficiently.

**Acceptance Criteria:**
- [ ] Tool `reqif.export_req_set` accepts query filters and format parameter
- [ ] Supports format=json (array of requirement records)
- [ ] Supports format=arrow_ipc (Apache Arrow streaming format)
- [ ] Supports format=parquet_ref (writes Parquet file and returns path)
- [ ] Export is deterministic (same query → same output)
- [ ] Large exports handle memory efficiently (streaming where possible)

### Phase 6: Integration & Testing

### US-020: End-to-end integration test
**Description:** As a system tester, I need an end-to-end test that exercises all components so that system integration is verified.

**Acceptance Criteria:**
- [ ] Test seeds ReqIF baseline with sample requirements
- [ ] Test runs stub agent to produce facts for target
- [ ] Test invokes OPA evaluation with bundle
- [ ] Test generates SARIF report
- [ ] Test writes verification event to store
- [ ] Test validates SARIF output against schema
- [ ] Test asserts trace links present (requirement → event → SARIF)
- [ ] Test asserts artifact hashes match
- [ ] Test runs in CI and fails on assertion errors

### US-021: ReqIF parser unit tests
**Description:** As a developer, I need comprehensive ReqIF parser tests so that edge cases are handled correctly.

**Acceptance Criteria:**
- [ ] Test: parse well-formed ReqIF XML successfully
- [ ] Test: reject malformed XML with clear error
- [ ] Test: handle invalid references in ReqIF (missing SpecType, etc.)
- [ ] Test: handle datatype mismatches in AttributeValues
- [ ] Test: handle empty ReqIF (no SpecObjects)
- [ ] Test: handle large ReqIF (>1000 requirements)
- [ ] All tests pass with clear assertions

### US-022: OPA policy bundle tests
**Description:** As a policy author, I need tests for OPA policies so that rubric logic is verified.

**Acceptance Criteria:**
- [ ] Test suite included in OPA bundle directory (tests/ or *_test.rego)
- [ ] Tests use golden inputs (sample requirement + facts)
- [ ] Tests assert expected decision object (status, criteria, score)
- [ ] Test edge cases: missing facts, invalid input, boundary conditions
- [ ] Tests can be run with `opa test` command
- [ ] CI runs OPA tests and fails build on test failures

### US-023: Query correctness tests
**Description:** As a developer, I need tests for requirement queries so that filtering logic is correct.

**Acceptance Criteria:**
- [ ] Test: filter by single subtype returns correct subset
- [ ] Test: filter by multiple subtypes (AND logic) works correctly
- [ ] Test: filter by baseline returns only requirements from that baseline
- [ ] Test: filter by status (active/obsolete) works correctly
- [ ] Test: pagination with limit/offset returns consistent results
- [ ] Test: empty query (no filters) returns all requirements
- [ ] Test: query with no matches returns empty array

### US-024: SARIF mapping invariant tests
**Description:** As a quality engineer, I need tests for SARIF mapping invariants so that reports are consistent.

**Acceptance Criteria:**
- [ ] Test: OPA fail status → SARIF error result
- [ ] Test: OPA pass status → no result or note result
- [ ] Test: OPA conditional_pass → SARIF warning result
- [ ] Test: rule.id matches requirement uid/key (stable)
- [ ] Test: result.locations present when evidence has code spans
- [ ] Test: property bag includes all required fields
- [ ] Test: each failing criterion produces a result

### Phase 7: Resources & Deployment

### US-025: Implement versioned resources
**Description:** As a CI pipeline, I want to access requirements via MCP resources so that I can retrieve individual requirements efficiently.

**Acceptance Criteria:**
- [ ] Resource `reqif://baseline/{id}` returns baseline metadata (id, version, hash, requirement count)
- [ ] Resource `reqif://requirement/{uid}` returns single requirement record by uid
- [ ] Resources follow FastMCP 3.0 versioning conventions
- [ ] Resources return 404 for non-existent baseline/requirement
- [ ] Resources support HTTP GET when server is in HTTP mode
- [ ] Resource URIs documented for client developers

### US-026: Create deployment documentation
**Description:** As a DevOps engineer, I need deployment documentation so that I can run the system in different environments.

**Acceptance Criteria:**
- [ ] Documentation covers local development setup (prerequisites, build, run)
- [ ] Documentation covers CI/CD integration (GitHub Actions example, GitLab CI example)
- [ ] Documentation covers containerized deployment (Dockerfile, docker-compose example)
- [ ] Documentation explains configuration options (OPA endpoint, bundle path, evidence store path)
- [ ] Documentation includes troubleshooting section
- [ ] Documentation includes architecture diagram

### US-027: Create sample CI pipeline configuration
**Description:** As a CI engineer, I want a sample CI configuration so that I can integrate the compliance gate into my pipeline.

**Acceptance Criteria:**
- [ ] Sample GitHub Actions workflow file provided
- [ ] Sample GitLab CI config file provided
- [ ] Sample shows how to start MCP server in CI
- [ ] Sample shows how to query requirements
- [ ] Sample shows how to run agent and evaluate
- [ ] Sample shows how to publish SARIF artifact
- [ ] Sample shows how to fail pipeline on compliance gate failure

## Functional Requirements

### ReqIF Server
- FR-1: The system must parse ReqIF 1.2 XML documents and extract SpecObjects, SpecTypes, and AttributeValues
- FR-2: The system must normalize ReqIF data into requirement records conforming to `reqif-mcp/1` schema
- FR-3: The system must validate requirement records for structural integrity and referential consistency
- FR-4: The system must provide query interface filtering by subtypes, baseline, status, with pagination support
- FR-5: The system must expose FastMCP 3.0 tools via HTTP and STDIO transports
- FR-6: The system must provide versioned resources for baselines and individual requirements

### OPA Integration
- FR-7: The system must compose OPA evaluation input from requirement + facts + context
- FR-8: The system must invoke OPA engine (local or REST API) with loaded policy bundles
- FR-9: The system must return structured decision objects with status, criteria, score, confidence, reasons, and policy provenance
- FR-10: The system must enable OPA decision logging for audit trail
- FR-11: The system must validate OPA output conforms to expected decision schema

### Agent Contract
- FR-12: The system must define a standard agent runner interface accepting subtype and artifacts path
- FR-13: The system must define `facts/1` schema for agent output with target, facts, evidence, and agent metadata
- FR-14: The system must provide a stub agent for integration testing

### SARIF Reporting
- FR-15: The system must generate SARIF v2.1.0 compliant reports from OPA decisions
- FR-16: The system must map OPA status to SARIF result.level per normative rules (fail→error, conditional_pass→warning, etc.)
- FR-17: The system must include requirement uid/key as stable SARIF rule.id
- FR-18: The system must map evidence pointers to SARIF result.locations
- FR-19: The system must include property bag with requirement_uid, policy_baseline.version, opa.policy.hash, agent.version
- FR-20: The system must validate SARIF output against official SARIF v2.1.0 JSON schema

### Evidence & Traceability
- FR-21: The system must write verification events linking requirement → target → decision → SARIF artifact
- FR-22: The system must store verification events in append-only JSONL log
- FR-23: The system must store SARIF artifacts and OPA decision logs with unique identifiers
- FR-24: The system must export requirement sets in JSON, Arrow IPC, or Parquet formats

### Testing
- FR-25: The system must include unit tests for ReqIF parsing (well-formed, malformed, invalid refs, datatypes)
- FR-26: The system must include OPA policy tests with golden inputs and expected decisions
- FR-27: The system must include query correctness tests (filters, pagination, determinism)
- FR-28: The system must include SARIF mapping invariant tests
- FR-29: The system must include end-to-end integration test exercising full workflow

## Non-Goals (Out of Scope for MVP)

- No multi-tenancy or access control (single-tenant prototype)
- No web UI for browsing requirements or viewing results (CLI/API only)
- No requirement authoring or editing tools (ingestion only)
- No sophisticated lifecycle management (supersession/obsolescence structure defined but minimal implementation)
- No real-time streaming or pub/sub (batch evaluation only)
- No advanced analytics or dashboards (raw data stores only)
- No OPA bundle signing verification (signature support mentioned but not enforced)
- No high-availability or distributed deployment (single-instance is acceptable)
- No advanced agent orchestration (manual agent invocation)
- No automatic policy baseline updates (manual bundle management)
- No optimization for massive scale (100s of requirements, not 10,000s)

## Design Considerations

### Data Model
- ReqIF is the single source of truth for requirements
- Normalized requirement records are derived views, rebuilt from ReqIF on demand
- Evidence stores are append-only for immutability and auditability
- All schemas versioned (reqif-mcp/1, facts/1) for forward compatibility

### Policy Architecture
- OPA policies are rubric-specific (one package per subtype or evaluation domain)
- Gate policies are separate from rubric policies (rubric=evaluate criteria, gate=aggregate decisions)
- Policy bundles include data/ for lookup tables, making policies more maintainable
- Policy provenance (bundle hash) required for reproducibility

### Interoperability
- SARIF v2.1.0 is the primary output format for IDE/tool integration
- ReqIF 1.2 is the input format for requirements (standard in automotive, aerospace, defense)
- OPA decision logs provide audit trail in standard OPA format
- Arrow/Parquet support enables integration with data science tooling

### Flexibility
- FastMCP 3.0 supports both HTTP (CI/CD) and STDIO (local dev)
- OPA can run locally (opa binary) or remote (REST API)
- Evidence storage is file-based (portable, no database required)
- Agent contract allows pluggable fact extractors

## Technical Considerations

### Dependencies
- FastMCP 3.0 SDK (Python or TypeScript, depending on implementation language)
- OPA binary or OPA library (Go) for policy evaluation
- XML parser (lxml for Python, xml2js for TypeScript, etc.)
- JSON Schema validator for schema conformance checks
- SARIF schema for validation (from official SARIF repo)

### Language Choice
- Recommend Python for rapid prototyping (strong XML/data processing libraries)
- Alternative: TypeScript if FastMCP ecosystem prefers JS/TS
- OPA policies are in Rego (language-agnostic)

### Performance Expectations (MVP)
- Parse ReqIF with 100-500 requirements in <5 seconds
- Query requirements in <100ms for typical filters
- OPA evaluation <500ms per requirement (depends on policy complexity)
- SARIF generation <1 second for 50 requirement results
- End-to-end evaluation (100 requirements) completes in <5 minutes

### Storage Estimates (MVP)
- ReqIF XML: 1-10 MB per baseline
- Normalized requirements: ~5-10 KB per requirement
- SARIF reports: ~10-50 KB per evaluation run
- Decision logs: ~2-5 KB per evaluation
- Total evidence store: <500 MB for 1000 evaluations

### Error Handling
- All tools return structured errors (error codes, messages, context)
- OPA evaluation failures do not crash server (return inconclusive status)
- SARIF validation failures logged but do not block report generation (best-effort)
- ReqIF parsing errors include line numbers and element paths for debugging

### Observability (Basic)
- Structured logging (JSON) to stderr
- Log levels: ERROR, WARN, INFO, DEBUG
- Key events logged: parse start/end, evaluation start/end, SARIF write, verification write
- No metrics/telemetry in MVP (could be added later)

## Success Metrics

- System can ingest a ReqIF baseline with 100 requirements and normalize to requirement records in <5 seconds
- OPA policies evaluate 50 requirements against stub facts in <30 seconds
- Generated SARIF reports validate successfully against SARIF v2.1.0 schema (100% conformance)
- End-to-end integration test passes: ReqIF → agent facts → OPA eval → SARIF → verification event
- Query performance: retrieve 20 requirements by subtype in <100ms
- Zero data loss: all verification events written to append-only log
- Proof of concept demonstrated to stakeholders (all components working together)

## Open Questions

### Technical
1. Should the ReqIF server maintain in-memory index or rebuild from XML on each query? (Tradeoff: startup time vs. query performance)
2. Should OPA run in-process (embedded) or as separate process/service? (Tradeoff: latency vs. isolation)
3. Should SARIF reports include passing results or only failures/warnings? (Tradeoff: completeness vs. report size)
4. Should evidence store use filesystem directly or abstract storage layer? (Tradeoff: simplicity vs. future flexibility)

### Process
5. Who is responsible for creating OPA policy bundles? (Policy authors, or generated from requirements?)
6. How often should policy baselines be updated? (On every requirement change, or versioned releases?)
7. Should supersession links be validated at parse time or query time? (Tradeoff: validation thoroughness vs. parse performance)

### Scope Clarifications
8. Are there specific subtypes to prioritize for the stub agent? (e.g., CYBER, ACCESS_CONTROL, or generic examples?)
9. Should the MVP support multiple ReqIF baselines simultaneously, or single baseline at a time?
10. Are there specific CI platforms to prioritize for sample configurations? (GitHub Actions, GitLab CI, Jenkins, etc.)
