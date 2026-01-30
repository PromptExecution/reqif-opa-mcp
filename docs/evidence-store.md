# Evidence Store

## Overview

The evidence store is an immutable, append-only repository for compliance gate execution artifacts. It captures the complete audit trail for requirement evaluations including verification events, SARIF reports, and OPA decision logs.

**Directory**: `evidence_store/`

**Design Principles**:
- **Immutability**: Events are append-only; modification requires governance approval
- **Traceability**: Every evaluation has unique ID (ULID) linking artifacts
- **Auditability**: Complete provenance chain from requirement to decision to SARIF
- **Temporal ordering**: ULIDs provide sortable, time-ordered identifiers

## Directory Structure

```
evidence_store/
├── events/              # Verification events (JSONL)
├── sarif/               # SARIF report artifacts (JSON)
└── decision_logs/       # OPA decision logs (JSONL)
```

### events/

**Purpose**: Records verification events linking requirements to evaluations

**Format**: JSONL (JSON Lines) - one verification event per line

**File**: `verifications.jsonl`

**Schema**: `schemas/verification-event.schema.json`

**Structure**:
```json
{
  "event_id": "01HQXYZ...",
  "requirement_uid": "REQ-CYBER-001",
  "target": {
    "repo": "github.com/org/project",
    "commit": "abc123...",
    "build": "2026-01-31-12345"
  },
  "decision": {
    "status": "pass",
    "score": 0.95,
    "confidence": 0.85
  },
  "timestamp": "2026-01-31T10:15:30Z",
  "sarif_ref": "01HQXYZ_compliance.sarif"
}
```

**Key Fields**:
- `event_id`: Unique ULID for this verification event
- `requirement_uid`: Links to specific requirement from baseline
- `target`: What was evaluated (repo, commit, build)
- `decision`: Summary of OPA evaluation (status, score, confidence)
- `timestamp`: ISO 8601 date-time of evaluation
- `sarif_ref`: Filename or path of corresponding SARIF artifact in `sarif/` directory

**Usage**:
- Written by `reqif.write_verification` MCP tool
- Append-only - new events always added at end
- Supports concurrent writes via unique file names or locking

**Query Patterns**:
- Filter by requirement_uid to get evaluation history for specific requirement
- Filter by target.repo to get all evaluations for a repository
- Filter by decision.status to find failures or warnings
- Sort by timestamp (implicit via ULID ordering) for temporal analysis

### sarif/

**Purpose**: Stores SARIF v2.1.0 compliance report artifacts

**Format**: JSON (pretty-printed for readability)

**Naming Convention**: `{evaluation_id}_{context}.sarif`

**Example Filenames**:
- `01HQXYZ_compliance.sarif`
- `01HQXYZ_cyber.sarif`
- `01HQXYZ_access_control.sarif`

**Schema**: SARIF v2.1.0 (`schemas/sarif-schema-2.1.0.json`)

**Usage**:
- Written by SARIF producer module after OPA evaluation
- Each SARIF file corresponds to one or more requirement evaluations
- Files are referenced by `sarif_ref` field in verification events
- CI/CD pipelines publish these as build artifacts for ingestion by code scanning tools

**SARIF Structure** (condensed):
```json
{
  "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/schemas/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "org.compliance",
        "version": "2026.01"
      }
    },
    "results": [{
      "ruleId": "REQ-CYBER-001",
      "level": "error",
      "message": {"text": "Crypto library usage not detected..."},
      "locations": [...],
      "properties": {
        "requirement_uid": "REQ-CYBER-001",
        "evaluation_id": "01HQXYZ...",
        "policy_baseline_version": "2026.01",
        "opa_policy_hash": "sha256:...",
        "agent_version": "stub-agent/0.1.0"
      }
    }]
  }]
}
```

**Key Properties**:
- `ruleId`: Requirement UID (stable identifier)
- `level`: error (fail), warning (conditional_pass, inconclusive), note (pass)
- `properties`: Traceability metadata linking back to requirement, policy, agent

### decision_logs/

**Purpose**: Captures complete OPA evaluation inputs and outputs for audit

**Format**: JSONL (JSON Lines) - one decision log entry per line

**File**: `decisions.jsonl`

**Structure**:
```json
{
  "evaluation_id": "01HQXYZ...",
  "timestamp": "2026-01-31T10:15:30Z",
  "requirement": { /* full requirement record */ },
  "facts": { /* full agent facts */ },
  "context": { /* evaluation context */ },
  "decision": { /* full OPA output */ },
  "policy": {
    "bundle": "org/compliance",
    "revision": "2026.01",
    "hash": "sha256:..."
  }
}
```

**Key Fields**:
- `evaluation_id`: Unique ULID linking to verification event and SARIF
- `timestamp`: ISO 8601 date-time of evaluation
- `requirement`: Complete requirement record (reqif-mcp/1)
- `facts`: Complete agent facts (facts/1)
- `context`: Evaluation context (flexible, may include CI metadata)
- `decision`: Complete OPA decision output (opa-output/1)
- `policy`: Policy provenance (bundle, revision, hash)

**Usage**:
- Written by OPA evaluator module during `evaluate_requirement()`
- Enabled by default with `enable_decision_logging=True`
- Log failures are non-fatal (warn and continue)
- Provides complete audit trail for reproducing evaluations

**Log Rotation**:
See README section 9.1 for log rotation strategy.

**MVP**: Single file without automatic rotation
**Production**: Use external tools like `logrotate` for rotation

## Traceability Chain

Every compliance gate evaluation creates a traceability chain:

```
Requirement (ReqIF baseline)
    ↓
Agent Facts (facts/1)
    ↓
OPA Evaluation
    ↓
Decision Log (decision_logs/decisions.jsonl)
    ↓
SARIF Report (sarif/{evaluation_id}.sarif)
    ↓
Verification Event (events/verifications.jsonl)
```

**Unique Identifier**: `evaluation_id` (ULID) links all artifacts

**Query Example**: Given verification event with `event_id=01HQXYZ`:
1. Read event from `events/verifications.jsonl` → get `sarif_ref` and `requirement_uid`
2. Read SARIF from `sarif/01HQXYZ_compliance.sarif` → get detailed results
3. Read decision log from `decision_logs/decisions.jsonl` where `evaluation_id=01HQXYZ` → get full inputs/outputs
4. Use `requirement_uid` to query original requirement from baseline

## Data Governance

### Immutability

- **Never modify** existing events, SARIF files, or decision logs
- **Never delete** artifacts without documented governance approval
- If correction needed, append correcting event with reference to original

### Retention Policy

- **Development/MVP**: Keep all artifacts indefinitely (small scale)
- **Production**: Define retention policy based on compliance requirements
  - Example: Keep 90 days active, 7 years archived
  - Consider legal/regulatory requirements (SOC2, ISO 27001, etc.)

### Access Control

- **Write**: CI/CD pipelines and MCP server only
- **Read**: Auditors, compliance officers, developers (read-only)
- **Modify**: Governance process only (with justification and approval)

### Backup and Archival

- **Backup**: Regular backups of `evidence_store/` directory
- **Archival**: Consider migrating old events to Parquet or data warehouse
  - Example: Convert JSONL to Parquet partitioned by date/subtype/baseline
  - Enables efficient analytics queries (e.g., "all CYBER failures in Q1 2026")

## Analytics and Reporting

### Example Queries (conceptual)

**Find all failures for requirement**:
```bash
grep '"requirement_uid": "REQ-CYBER-001"' evidence_store/events/verifications.jsonl | \
  jq 'select(.decision.status == "fail")'
```

**Count evaluations by status**:
```bash
jq -s 'group_by(.decision.status) | map({status: .[0].decision.status, count: length})' \
  evidence_store/events/verifications.jsonl
```

**Find all evaluations for repository**:
```bash
jq 'select(.target.repo == "github.com/org/project")' \
  evidence_store/events/verifications.jsonl
```

### Future: Data Warehouse Integration

For production scale, consider:
- Export JSONL to Parquet for columnar analytics
- Partition by date, subtype, baseline, status
- Use SQL queries for compliance dashboards
- Example tools: DuckDB, ClickHouse, BigQuery, Snowflake

## File Size Considerations

### Development/MVP
- Expected: <1000 evaluations
- File sizes: <10MB JSONL, <100MB total

### Production Scale
- Expected: >100k evaluations/year
- File sizes: >1GB JSONL per year
- **Recommendation**: Implement log rotation and archival strategy
  - Rotate daily or weekly
  - Archive to compressed format (gzip JSONL or Parquet)
  - Use database or data warehouse for long-term storage

## Error Handling

### Write Failures

If write to evidence store fails:
- **Decision logs**: Log warning and continue (non-fatal)
- **Verification events**: Return error to caller (critical for traceability)
- **SARIF files**: Return error to caller (required for CI/CD)

### Concurrent Writes

**MVP**: Single-threaded CI pipeline, no concurrency issues

**Production**: Consider:
- File locking for JSONL appends (fcntl, flock)
- Unique filenames per evaluation (e.g., `{evaluation_id}_verifications.jsonl`)
- Merge separate files during rotation/archival

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run compliance gate
  run: |
    # Evaluate and generate SARIF
    python -m compliance_gate \
      --requirement REQ-CYBER-001 \
      --artifacts ./build \
      --output evidence_store/sarif/${{ github.run_id }}_compliance.sarif

    # Write verification event
    python -m compliance_gate write-event \
      --evaluation-id ${{ github.run_id }} \
      --requirement REQ-CYBER-001 \
      --status $STATUS \
      --sarif-ref ${{ github.run_id }}_compliance.sarif

- name: Upload SARIF artifact
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: evidence_store/sarif/${{ github.run_id }}_compliance.sarif

- name: Archive evidence store
  uses: actions/upload-artifact@v3
  with:
    name: evidence-store
    path: evidence_store/
```

## Summary

The evidence store provides:
- ✅ **Complete audit trail**: All artifacts for every evaluation
- ✅ **Immutable history**: Append-only, no modifications
- ✅ **Traceability**: Unique IDs link requirement → decision → SARIF
- ✅ **Compliance**: Supports SOC2, ISO 27001, regulatory audits
- ✅ **Analytics**: JSONL format enables queries and reporting
- ✅ **CI/CD integration**: SARIF artifacts publish to code scanning tools

**Next Steps**:
1. Implement `reqif.write_verification` MCP tool (US-027)
2. Add end-to-end integration test (US-030)
3. Define production log rotation strategy (external to MVP)
4. Consider Parquet export for analytics (post-MVP)
