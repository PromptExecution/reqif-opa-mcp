ReqIF→OPA→SARIF Compliance Gate System (FastMCP 3.0) — Spec-Driven, OSS/Standards-First
Normative standards / formats

ReqIF 1.2 (requirements interchange, XML).

SARIF v2.1.0 (OASIS Standard) (static analysis results interchange).

OPA policy bundles (policy+data distribution; optional signatures).

OPA decision logs (auditable record of each policy query).

OPA in CI/CD (policy-as-code gates).

FastMCP 3.0 server scaffolding + HTTP transport + versioned resources.

Opinionated ecosystem

GitOps/CI produces artifacts (code diff, build outputs, infra manifests, SBOM, test reports).

Deterministic compliance = OPA; semantic extraction = agent skills.

Compliance UI + interchange = SARIF (primary), plus OPA decision logs (audit), plus ReqIF trace links (governance).

1) System objective

Given:

Requirements (ReqIF) with subtype(s) and evaluation rubric references,

A target (commit/changeset/build artifact),

Agent-produced structured facts,

Produce:

OPA decision(s) (deterministic),

SARIF run(s) (portable reporting),

Traceable verification evidence linked to requirement UID and target revision,

Repeatable gates suitable for CI/CD.

2) High-level architecture
flowchart LR
  subgraph R["Requirements Authority"]
    A["ReqIF MCP Server (FastMCP 3.0)"]
    S["ReqIF raw store (immutable)"]
    N["Normalized model + indexes (derived)"]
    A --> S
    A --> N
  end

  subgraph P["Policy & Evaluation"]
    B["OPA (policy engine)"]
    PB["OPA Bundles (policies+data)"]
    DL["OPA Decision Logs (audit)"]
    B <-- bundle pull --> PB
    B --> DL
  end

  subgraph E["Evidence & Reporting"]
    AR["Agent(s): subtype skill runners"]
    SAR["SARIF Producer"]
    EV["Evidence Store (JSONL/Arrow/Parquet)"]
  end

  subgraph C["CI/CD / GitOps"]
    CI["Pipeline Job"]
    ART["Artifacts: diff, build outputs, manifests, SBOM, test data"]
  end

  CI --> ART
  CI -->|fetch reqs| A
  ART --> AR
  A -->|req subset + rubric refs| AR
  AR -->|facts JSON| B
  A -->|req context| B
  B -->|decision + reasons| SAR
  AR -->|evidence refs| SAR
  SAR --> EV
  SAR --> CI
  EV --> A

3) Responsibilities (strict separation)
ReqIF MCP server (authority)

Parse/validate ReqIF.

Maintain requirement lifecycle: versions, status (active/obsolete), supersession links.

Serve requirement subsets by subtype, policy baseline, and scope.

Accept verification events and attach trace links.

OPA (deterministic gate)

Evaluate rubric rules against facts + requirement metadata.

Return structured decision object (not just allow/deny).

Emit decision logs for audit.

Consume policies/data via bundles (+ signatures if required).

Agents (semantic/heuristic)

Turn changeset/build artifacts into typed facts.

Never decide pass/fail directly; only produce facts + evidence pointers.

SARIF producer (report interoperability)

Translate: requirement ↔ rule, evaluation ↔ result.

Primary output format for CI ingestion and aggregation.

4) Data contracts (normative)
4.1 Requirement record (server output)

Minimal normalized JSON (schema reqif-mcp/1):

{
  "uid": "uuid|ulid|reqif-identifier",
  "key": "CYBER-AC-001",
  "subtypes": ["CYBER","ACCESS_CONTROL"],
  "status": "active|obsolete|draft",
  "policy_baseline": {"id":"POL-2026.01","version":"2026.01","hash":"..."},
  "rubrics": [{"engine":"opa","bundle":"org/cyber","package":"cyber.access_control.v3","rule":"decision"}],
  "text": "requirement statement",
  "attrs": {"severity":"high","owner":"...","verify_method":"analysis|test|inspection|demo"}
}

4.2 Agent facts (OPA input)

Schema facts/1 (typed, evidence-addressable):

{
  "target": {"repo":"...","commit":"...","build":"..."},
  "facts": {
    "uses_crypto_library": true,
    "inputs_validated": [{"path":"src/x.rs","line":44,"kind":"missing"}],
    "sbom": {"cyclonedx_ref":"..."},
    "diff_summary": {"files_changed": 12}
  },
  "evidence": [
    {"type":"code_span","uri":"repo://.../src/x.rs","startLine":40,"endLine":55},
    {"type":"artifact","uri":"artifact://sbom.cdx.json","hash":"sha256:..."}
  ],
  "agent": {"name":"cyber-agent","version":"x.y","rubric_hint":"cyber.access_control.v3"}
}

4.3 OPA evaluation input (composed)

OPA input = { requirement, facts, context }.

OPA output MUST be:

{
  "status": "pass|fail|conditional_pass|inconclusive|not_applicable|blocked|waived",
  "score": 0.0,
  "confidence": 0.0,
  "criteria": [
    {"id":"AC-1","status":"pass|fail|na","weight":3,"message":"...","evidence":[0,2]}
  ],
  "reasons": ["..."],
  "policy": {"bundle":"org/cyber","revision":"...", "hash":"..."}
}


Decision logs MUST be enabled for audit.

4.4 SARIF output mapping (normative)

One SARIF run per pipeline evaluation unit (e.g., per subtype or per rubric bundle).

SARIF tool.driver.name = rubric bundle ID.

SARIF rule.id = requirement uid OR stable key (choose one; MUST be stable).

SARIF result.level mapping:

pass → omit result (preferred) OR note

conditional_pass → warning

fail → error

inconclusive|blocked → warning + property triage=needed

not_applicable → omit result

SARIF result.message = concise reason(s).

Evidence pointers:

result.locations[] from code spans/artifacts where available.

SARIF properties MUST carry:

requirement_uid, requirement_key, subtypes[], policy_baseline.version, opa.policy.hash, agent.version.

SARIF is the standard interchange for static analysis results.

5) Workflows (normative)
5.1 Policy distillation → requirements publication
sequenceDiagram
  participant Author as Policy Authoring (source docs)
  participant Distill as Distillation Pipeline
  participant Req as ReqIF MCP Server
  participant OPA as OPA Bundle Registry

  Author->>Distill: Update policy baseline (vNext)
  Distill->>Distill: Extract requirements + subtypes + rubric refs
  Distill->>Req: Publish ReqIF package (new baseline)
  Distill->>OPA: Publish OPA bundle revision (matching baseline)
  Req-->>Distill: Baseline handle + hash
  OPA-->>Distill: Bundle revision + hash

5.2 CI/CD evaluation gate (changeset)
sequenceDiagram
  participant CI as CI Job
  participant Req as ReqIF MCP Server
  participant Agent as Subtype Agent Runner
  participant OPA as OPA
  participant SAR as SARIF Producer
  participant Store as Evidence Store

  CI->>Req: query requirements by subtype(s) + scope
  Req-->>CI: req set (uid/key/text/rubrics)
  CI->>Agent: run agent(skill=subtype) on artifacts/diff
  Agent-->>CI: facts+evidence refs
  CI->>OPA: evaluate (req + facts + context)
  OPA-->>CI: decision(status/criteria/score)
  CI->>SAR: emit SARIF(run)
  SAR-->>CI: sarif.json
  CI->>Store: append evaluation record + SARIF
  CI->>Req: write verification event (trace link)

5.3 Requirement lifecycle (supersession, obsolescence)
flowchart TD
  R1["Req(uid=U1,key=CYBER-AC-001,status=active,baseline=2026.01)"]
  R2["Req(uid=U2,key=CYBER-AC-001,status=active,baseline=2026.02)"]
  R1 -->|"supersededBy"| R2
  R1 -->|"status=obsolete"| R1

6) Gate criteria model (beyond pass/fail)

Status set (closed):

pass

fail

conditional_pass

inconclusive

blocked (missing artifacts / insufficient facts)

not_applicable

waived (explicit exception with approval ref)

Quantities (optional, but supported):

score ∈ [0,1] (weighted rubric)

confidence ∈ [0,1] (agent quality + evidence strength)

coverage ∈ [0,1] (criteria evaluated / criteria total)

severity ∈ {low,med,high,critical} (requirement attribute)

Gate policies (OPA-level, separate from rubric):

Block release if any fail for severity>=high

Block if coverage < threshold

Block if any blocked for required subtypes

Allow conditional_pass for non-critical, but annotate SARIF

OPA is explicitly used as CI/CD guardrails.

7) FastMCP 3.0 server surface (normative)

Transport:

HTTP (streamable) for multi-client CI usage.

STDIO optional for local/dev.

Core tools (MVP):

reqif.parse(xml_b64) -> handle

reqif.validate(handle, mode=basic|strict) -> report

reqif.query(where, baseline, subtypes[], status, limit, offset) -> req[]

reqif.write_verification(event) -> ok

reqif.export_req_set(format=json|arrow_ipc|parquet_ref) -> artifact_ref

Resources (versioned):

reqif://baseline/{id} (returns metadata + hashes)

reqif://requirement/{uid}

FastMCP 3.0 provides tools, HTTP transport, and versioned resources.

8) OPA integration (normative)

Policy distribution:

OPA bundles, optionally signed.

Bundle contains:

policy/*.rego

data/*.json (optional lookup tables, thresholds, subtype maps)

Evaluation endpoint:

Local opa eval or OPA REST API (implementation choice).

Input must include policy.bundle hash/revision (for provenance).

Audit:

Decision logs enabled; shipped to evidence store.

9) Evidence storage (OSS-first)

Authoritative vs derived:

Authority: ReqIF XML + requirement graph.

Evidence: append-only event log + columnar projections.

Required stores:

JSONL event log (append-only)

Parquet (partitioned by date/subtype/baseline) for analytics

SARIF artifacts saved verbatim

(Arrow/Parquet are implementation choices; contract is "tabular + immutable events".)

9.1 Log rotation strategy (decision logs)

Decision logs are written to evidence_store/decision_logs/decisions.jsonl as an append-only JSONL file.

Log rotation strategy (for production deployment):

Manual rotation: Use external log rotation tools (logrotate, systemd, or cloud-native solutions)

Rotation schedule: Daily or when log file exceeds size threshold (e.g., 100MB)

Compressed archives: After rotation, compress with gzip or similar (decisions.jsonl.2026-01-31.gz)

Retention policy: Keep compressed logs for audit period (e.g., 7 years for compliance)

Naming convention: decisions.jsonl.<date>.gz for archived logs

For MVP: Decision logs are written to single file without automatic rotation. Production deployments should configure external rotation tools.

Decision logs are immutable audit trail - never modify or delete logs without governance approval.

10) Test specification (must be implemented)
10.1 Unit tests

ReqIF parse/validate:

well-formed, invalid refs, datatype mismatch.

Query correctness:

subtype filter, baseline filter, status filter, pagination determinism.

Lifecycle:

supersession graph invariants.

10.2 OPA policy tests (bundle-contained)

For each rubric package:

golden inputs → expected {status, criteria[], score}.

Gate policy tests:

mixtures of results → expected release decision.

(OPA supports CI/CD usage and is typically policy-tested; bundle testing is standard practice in the ecosystem.)

10.3 Integration tests

End-to-end:

seed ReqIF baseline

run agent stub to emit facts

run OPA with bundle

produce SARIF

write verification event

assert trace links and artifact hashes

10.4 SARIF conformance tests

Validate SARIF against SARIF v2.1.0 schema (use an OSS validator).

Verify mapping invariants:

each failing criterion emits result.level=error

rule ids stable

locations present when evidence has code spans

SARIF is standardized; conformance is testable.

11) Minimal deliverables (MVP)

FastMCP 3.0 ReqIF MCP server with tools/resources above.

OPA bundle template:

rubric package per subtype

gate policy package

bundle metadata & optional signatures.

Agent runner contract (facts/1) + stub agent.

SARIF producer implementing the normative mapping.

Test suite: unit + opa policy tests + integration + sarif validation.
