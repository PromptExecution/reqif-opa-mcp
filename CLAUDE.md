# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research prototype compliance gate system that transforms requirements from ReqIF format into deterministic policy evaluations (OPA) with standardized SARIF reporting. The system enables CI/CD pipelines to verify code changes against policy requirements through automated, auditable gates.

**Core Architecture**: ReqIF (requirements) → FastMCP 3.0 Server → Agent Facts → OPA Policy Evaluation → SARIF Reports → Evidence Store

## Code Style & Conventions

### Python Standards (from AGENTS.md)
- **Linting**: ALWAYS use `ruff`, NEVER black or other linters
- **Type Hints**: ALWAYS use PEP 484 type hints (https://peps.python.org/pep-0484/)
- **Package Management**: ALWAYS use `uv` or `uvx` (NEVER poetry or pip), PREFER pixi over conda
  - Avoid editing pyproject.toml directly; use uv commands
- **MCP Framework**: Use `fastmcp >= 0.4.0` (https://github.com/jlowin/fastmcp)
- **Web Framework**: Prefer FastAPI

### Error Handling Philosophy
Use DRY PYTHON "returns" module to emulate Rust Option/Result patterns:
```python
from returns.result import Result, Success, Failure
from returns.option import Option, Some, Nothing

def get_user(id: int) -> Result[str, Exception]:
    if id == 1:
        return Success("Alice")
    else:
        return Failure(ValueError("Not found"))

match get_user(2):
    case Success(user):
        print(user)
    case Failure(error):
        print(f"Oops: {error}")
```

Also use:
- PEP 654 grouped exceptions (native in Python 3.11): `raise ExceptionGroup("Multiple failures", [IOError("disk"), ValueError("bad input")])`
- Chained exceptions: `raise X from Y`
- Exception hierarchy with decorators/middleware
- `__str__`, `__repr__`, plus logging + traceback module

### Documentation Style
- Laconic docstring comments (from AGENTS.md: "laconic docstring comments, idiomatic justfiles for commands")
- It should not be necessary to read Python to understand abstract capabilities of a repo
- Use idiomatic justfiles for commands

## Data Contracts & Schemas

### Requirement Record (reqif-mcp/1)
```json
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
```

### Agent Facts (facts/1)
```json
{
  "target": {"repo":"...","commit":"...","build":"..."},
  "facts": {
    "uses_crypto_library": true,
    "inputs_validated": [{"path":"src/x.rs","line":44,"kind":"missing"}]
  },
  "evidence": [
    {"type":"code_span","uri":"repo://...","startLine":40,"endLine":55},
    {"type":"artifact","uri":"artifact://sbom.cdx.json","hash":"sha256:..."}
  ],
  "agent": {"name":"cyber-agent","version":"x.y","rubric_hint":"cyber.access_control.v3"}
}
```

### OPA Evaluation
**Input**: `{requirement, facts, context}`

**Output**:
```json
{
  "status": "pass|fail|conditional_pass|inconclusive|not_applicable|blocked|waived",
  "score": 0.0,
  "confidence": 0.0,
  "criteria": [
    {"id":"AC-1","status":"pass|fail|na","weight":3,"message":"...","evidence":[0,2]}
  ],
  "reasons": ["..."],
  "policy": {"bundle":"org/cyber","revision":"...","hash":"..."}
}
```

### SARIF Mapping (Normative)
- `pass` → omit result (or note)
- `fail` → error
- `conditional_pass` → warning
- `inconclusive|blocked` → warning + property `triage=needed`
- `not_applicable` → omit result
- `requirement uid` → SARIF `rule.id` (MUST be stable)
- Evidence pointers → `result.locations[]`
- Property bag MUST include: `requirement_uid`, `requirement_key`, `subtypes[]`, `policy_baseline.version`, `opa.policy.hash`, `agent.version`

## Component Responsibilities

### ReqIF MCP Server (Authority)
- Parse/validate ReqIF 1.2 XML
- Maintain requirement lifecycle (versions, status, supersession links)
- Serve requirement subsets by subtype, policy baseline, and scope
- Accept verification events and attach trace links
- FastMCP 3.0 tools: `reqif.parse`, `reqif.validate`, `reqif.query`, `reqif.write_verification`, `reqif.export_req_set`
- Resources: `reqif://baseline/{id}`, `reqif://requirement/{uid}`

### OPA (Deterministic Gate)
- Evaluate rubric rules against facts + requirement metadata
- Return structured decision object (not just allow/deny)
- Emit decision logs for audit
- Consume policies/data via bundles (+ signatures if required)

### Agents (Semantic/Heuristic)
- Turn changeset/build artifacts into typed facts
- NEVER decide pass/fail directly; only produce facts + evidence pointers
- Interface: `run_agent(subtype, artifacts_path, requirement_context) -> facts`
- MUST return error objects, not throw exceptions

### SARIF Producer (Report Interoperability)
- Translate: requirement ↔ rule, evaluation ↔ result
- Primary output format for CI ingestion and aggregation
- MUST validate against SARIF v2.1.0 schema

### Evidence Store (Audit Trail)
- Directory structure: `evidence_store/{events/,sarif/,decision_logs/}`
- JSONL event log (append-only)
- Parquet partitioned by date/subtype/baseline for analytics
- SARIF artifacts saved verbatim

## Testing Requirements

### Unit Tests
- **ReqIF parse/validate**: well-formed, invalid refs, datatype mismatch
- **Query correctness**: subtype filter, baseline filter, status filter, pagination determinism
- **Lifecycle**: supersession graph invariants

### OPA Policy Tests (bundle-contained)
- For each rubric package: golden inputs → expected `{status, criteria[], score}`
- Gate policy tests: mixtures of results → expected release decision
- Run with: `opa test`

### Integration Tests
- End-to-end: seed ReqIF baseline → run agent stub → run OPA with bundle → produce SARIF → write verification event
- Assert trace links and artifact hashes

### SARIF Conformance Tests
- Validate SARIF against SARIF v2.1.0 schema
- Verify mapping invariants:
  - Each failing criterion emits `result.level=error`
  - Rule ids are stable
  - Locations present when evidence has code spans

## Development Workflow

### Current State
This is a greenfield project. The README.md and PRD specify the complete architecture, but no implementation code exists yet. Development follows the Ralph autonomous agent system (see `ralph/prd.json` for detailed user stories).

### Implementation Priority
1. **Phase 1 (Foundation)**: ReqIF data model, parsing, normalization, schemas
2. **Phase 2**: OPA integration, policy bundles, evaluation engine
3. **Phase 3**: Agent contract, stub agent
4. **Phase 4**: SARIF reporting, mapping, validation
5. **Phase 5**: Evidence store, verification events, traceability
6. **Phase 6**: Integration tests, end-to-end validation
7. **Phase 7**: MCP resources, deployment docs, CI samples

### Key Design Principles
- **Strict separation of concerns**: Agents produce facts, OPA makes decisions, SARIF reports results
- **Deterministic compliance**: OPA handles policy evaluation; agents handle semantic extraction
- **Standards-first**: ReqIF 1.2, SARIF v2.1.0, OPA bundles are normative
- **Append-only evidence**: Immutability and auditability are paramount
- **Schema versioning**: All data contracts versioned (reqif-mcp/1, facts/1)

## Critical Implementation Notes

1. **Decision Logs MUST be enabled**: OPA decision logging is required for audit
2. **SARIF property bags are mandatory**: Must include requirement_uid, policy_baseline.version, opa.policy.hash, agent.version
3. **Query results must be deterministic**: Sort by uid (ascending) for consistent ordering
4. **Agents NEVER decide pass/fail**: Only produce facts; OPA makes decisions
5. **Evidence pointers are addressable**: Use stable URIs (repo://, artifact://)
6. **Policy provenance required**: Bundle hash/revision must be tracked for reproducibility

## Common Pitfalls to Avoid

- Don't let agents directly determine compliance status
- Don't skip SARIF schema validation
- Don't make query results non-deterministic
- Don't hardcode OPA bundle paths or policy packages
- Don't lose decision log audit trail
- Don't create mutable evidence stores

## Integration Points

### FastMCP 3.0 Server
- HTTP transport for multi-client CI usage
- STDIO optional for local/dev
- Tools and versioned resources

### CI/CD Pipeline
- Start FastMCP server
- Query requirements by subtype/baseline
- Run agent to produce facts
- Invoke OPA evaluation
- Generate SARIF report
- Write verification event
- Publish SARIF artifact
- Fail pipeline on `status=fail` for `severity>=high`

### OPA Bundles
- Bundle structure: `{policy/,data/,.manifest}`
- Policy files: `*.rego` with rubric package per subtype
- Data files: `*.json` for lookup tables, thresholds
- Metadata includes version and hash

## Ralph++ Autonomous Workflow

Ralph++ is an enhanced autonomous agent system that automatically transitions between completed PRDs and new GitHub issues, creating a continuous workflow until the backlog is clear.

### Complete Workflow

1. **Read PRD**: Check `ralph/prd.json` for user stories
2. **Implement**: Execute highest priority incomplete story
3. **Quality Check**: Run typecheck, lint, tests
4. **Commit**: Use conventional commits with story ID scope
5. **Update**: Mark story as `passes: true` in prd.json
6. **Archive**: When all stories complete, move prd.json to `.archive/prd-YYYYMMDD-HHMMSS-[project].json`
7. **Fetch Issue**: Get most recent open GitHub issue
8. **Convert**: Transform issue (body + comments) to prd.json format
9. **Create PR**: When issue completed, create PR with `gh pr create`
10. **Repeat**: Continue until no local prd.json and no open issues

### Exit Condition

Ralph exits when the backlog is clear:
- No `ralph/prd.json` exists
- No open GitHub issues found via `gh issue list --state open --limit 1`
- Prints: `✅ BACKLOG CLEAR - All issues completed!`

This indicates all work items have been processed and archived.

### Conventional Commit Requirement

When completing user stories from GitHub issues, commits must follow conventional commit format:

```
<type>(<scope>): <description>

<body>

Closes #<issue-number>
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Format Rules**:
- **Type**: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `chore` (maintenance)
- **Scope**: User story ID (e.g., `feat(US-042): implement health endpoint`)
- **Description**: User story title, max 72 characters
- **Body**: Acceptance criteria summary
- **Footer**: `Closes #<issue-number>` if from GitHub issue, plus co-author tag

### Pull Request Creation

When all user stories from a GitHub issue are completed (`passes: true`):

1. Create PR using `gh pr create`
2. PR title: `feat: <issue-title>` or `fix: <issue-title>` based on content
3. PR body template:
   ```
   ## Summary
   [user stories completed]

   ## Testing
   [test results]

   Closes #<number>
   ```
4. Use branch name from `prd.json` `branchName` field
5. Target branch: main or master (auto-detect default branch)
6. PR created only if on feature branch (not on main/master)
7. Return PR URL in completion message

### Troubleshooting

**gh CLI not installed**:
```bash
# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Authentication issues**:
```bash
# Authenticate with GitHub
gh auth login
# Or set token
export GITHUB_TOKEN=<your-token>
```

**Repository not configured**:
- Ralph requires a git repository with a GitHub remote
- Ensure you're in a git repo: `git status`
- Add GitHub remote if missing: `git remote add origin <repo-url>`

**Issue parsing failures**:
- Ensure issues follow template format with `### US-XXX:` user stories
- Check comments for additional requirements
- If no explicit user stories found, Ralph creates a single story from issue body
