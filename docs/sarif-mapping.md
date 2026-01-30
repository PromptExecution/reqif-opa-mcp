# SARIF Mapping Rules

## Overview

This document defines the normative mapping rules for transforming OPA policy evaluation decisions into SARIF (Static Analysis Results Interchange Format) v2.1.0 reports. These mappings ensure consistent, standards-compliant compliance reporting across all requirements, agents, and policy evaluations.

## Status Mapping

The OPA evaluation `status` field maps to SARIF `result.level` as follows:

| OPA Status | SARIF result.level | SARIF Inclusion | Notes |
|------------|-------------------|-----------------|-------|
| `pass` | `note` (optional) | Omit or include as note | Successful evaluations typically omitted from SARIF unless verbose reporting enabled |
| `fail` | `error` | Required | Compliance gate failure - MUST be reported |
| `conditional_pass` | `warning` | Required | Partial compliance - requires attention |
| `inconclusive` | `warning` | Required | Add property `triage=needed` |
| `blocked` | `warning` | Required | Add property `triage=needed` |
| `not_applicable` | N/A | Omit | Requirement not applicable to target - no result needed |
| `waived` | `note` | Optional | Waived requirements may be reported for audit trail |

### Mapping Rules

1. **Pass results**: Default behavior is to omit passing requirements from SARIF output to reduce noise. For audit/verbose reporting, pass results MAY be included with `level=note`.

2. **Fail results**: MUST be reported as `level=error`. This signals compliance gate failure.

3. **Conditional pass results**: MUST be reported as `level=warning`. These indicate partial compliance that may be acceptable in some contexts but requires review.

4. **Inconclusive/Blocked results**: MUST be reported as `level=warning` with property `triage=needed`. These indicate evaluation could not complete and require manual triage.

5. **Not applicable results**: MUST be omitted from SARIF output. If the requirement does not apply to the target, no result should be generated.

6. **Waived results**: MAY be included for audit purposes as `level=note` to preserve traceability of waiver decisions.

## Requirement to SARIF Rule Mapping

Each requirement in the ReqIF baseline maps to a SARIF `rule` object:

| Requirement Field | SARIF Field | Notes |
|------------------|-------------|-------|
| `uid` | `rule.id` | MUST be stable across evaluations for the same requirement |
| `key` | `rule.name` | Human-readable requirement key (e.g., "CYBER-AC-001") |
| `text` | `rule.fullDescription.text` | Full requirement statement |
| `subtypes[]` | `rule.properties.subtypes` | Requirement classification |
| `policy_baseline.version` | `rule.properties.policy_baseline_version` | Policy version for traceability |

### Rule Stability

**CRITICAL**: `rule.id` MUST use the requirement `uid` field to ensure stable, consistent identification across:
- Multiple evaluations of the same baseline
- Different commits/builds
- Historical trend analysis
- SARIF aggregation and merge operations

**DO NOT** use requirement `key` for `rule.id` if keys are subject to change. The `uid` field is the canonical stable identifier.

## Evidence to SARIF Location Mapping

Evidence pointers from agent facts map to SARIF `result.locations[]`:

| Evidence Type | SARIF Mapping | Notes |
|--------------|---------------|-------|
| `code_span` | `physicalLocation` | Maps to file URI, line range |
| `artifact` | `physicalLocation` or `relatedLocations` | Artifact files (SBOM, config, etc.) |
| `log` | `relatedLocations` | Log file references |
| `metric` | Not mapped directly | Metrics stored in property bag |

### Code Span Evidence Mapping

For evidence with `type=code_span`:

```json
{
  "type": "code_span",
  "uri": "repo://github.com/org/repo/src/auth.py",
  "startLine": 42,
  "endLine": 55
}
```

Maps to SARIF:

```json
{
  "physicalLocation": {
    "artifactLocation": {
      "uri": "src/auth.py",
      "uriBaseId": "SRCROOT"
    },
    "region": {
      "startLine": 42,
      "endLine": 55
    }
  }
}
```

**URI normalization rules**:
1. Strip `repo://github.com/org/repo/` prefix and extract relative path
2. Use `uriBaseId=SRCROOT` for source code locations
3. Use `uriBaseId=BINROOT` for build artifact locations

### Multiple Evidence Items

When `facts.evidence[]` contains multiple items:
- All evidence items with `type=code_span` MUST be mapped to `result.locations[]`
- Multiple locations indicate all code spans contributing to the decision
- Evidence array indices preserved via `result.properties.evidence_indices[]`

### Missing Evidence

If no evidence is provided (empty `facts.evidence[]`):
- `result.locations[]` MUST be omitted or empty
- Decision still valid - some facts are binary or derived without specific code locations

## Required SARIF Property Bag Fields

Every SARIF `result.properties` object MUST include the following fields for traceability and auditability:

| Property | Source | Type | Description |
|----------|--------|------|-------------|
| `requirement_uid` | `requirement.uid` | string | Stable requirement identifier |
| `requirement_key` | `requirement.key` | string | Human-readable requirement key |
| `subtypes` | `requirement.subtypes[]` | string[] | Requirement classification |
| `policy_baseline_version` | `requirement.policy_baseline.version` | string | Policy version used for evaluation |
| `opa_policy_hash` | `decision.policy.hash` | string | OPA bundle content hash for reproducibility |
| `agent_version` | `facts.agent.version` | string | Agent version that produced facts |
| `evaluation_id` | Decision log entry | string (ULID) | Links to decision log for audit |
| `timestamp` | Evaluation time | string (ISO 8601) | When evaluation occurred |

### Optional Property Bag Fields

Additional properties MAY be included for enhanced context:

- `triage` = `"needed"` for inconclusive/blocked results
- `opa_score` = decision score (0.0-1.0)
- `opa_confidence` = decision confidence (0.0-1.0)
- `target_repo` = repository URL from facts.target
- `target_commit` = commit hash from facts.target
- `criteria_summary` = summary of criterion pass/fail counts

## SARIF Run Object Structure

The SARIF report MUST include a properly structured `run` object:

```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "<OPA bundle identifier>",
          "version": "<bundle revision>",
          "informationUri": "https://github.com/org/opa-bundles",
          "rules": [...]
        }
      },
      "results": [...],
      "properties": {
        "policy_bundle": "<bundle id>",
        "policy_revision": "<bundle revision>",
        "policy_hash": "<bundle content hash>",
        "evaluation_time": "<ISO 8601 timestamp>"
      }
    }
  ]
}
```

### Tool Driver Fields

| Field | Value | Notes |
|-------|-------|-------|
| `tool.driver.name` | OPA bundle identifier from decision.policy.bundle | E.g., "org/cyber" |
| `tool.driver.version` | OPA bundle revision from decision.policy.revision | E.g., "2026.01" |
| `tool.driver.informationUri` | Bundle repository URL | Optional but recommended |
| `tool.driver.rules[]` | Array of SARIF rules | One rule per evaluated requirement |

## Result Message Construction

SARIF `result.message.text` field MUST be populated with clear, actionable information:

### Message Construction Rules

1. **Use OPA reasons**: Primary message content comes from `decision.reasons[]` array
2. **Join multiple reasons**: If multiple reasons, join with newlines or semicolons
3. **Fall back to criteria messages**: If no top-level reasons, aggregate `decision.criteria[].message`
4. **Include score/confidence**: Optionally append score and confidence for context

### Example Messages

**Fail result**:
```
Requirement CYBER-AC-001 failed: Missing cryptographic library usage; Input validation insufficient for user-provided data. (Score: 0.35, Confidence: 0.80)
```

**Warning result (conditional_pass)**:
```
Requirement CYBER-AC-001 partially satisfied: Cryptographic library used but weak algorithm detected (SHA-1). Consider upgrading to SHA-256. (Score: 0.65, Confidence: 0.90)
```

**Inconclusive result**:
```
Requirement CYBER-AC-001 evaluation inconclusive: Insufficient evidence collected. Manual review required. (Triage needed)
```

## Criterion-Level Mapping (Optional)

Individual criteria from `decision.criteria[]` MAY be mapped to separate SARIF results for granular reporting:

- Each criterion with `status=fail` generates a separate result
- Criterion `id` used as `result.ruleId` with suffix (e.g., "REQ-001.AC-1")
- Criterion `message` maps to `result.message.text`
- Criterion `evidence[]` indices map to `facts.evidence[]` for locations

**Trade-off**: Criterion-level mapping provides detailed breakdown but increases SARIF file size. Use for verbose/debug reporting only.

## Schema Validation Requirements

All generated SARIF output MUST:
1. Validate against SARIF v2.1.0 JSON Schema (https://json.schemastore.org/sarif-2.1.0.json)
2. Include `$schema` field pointing to schema URI
3. Include `version` field = "2.1.0"
4. Pass conformance checks via SARIF validator library

## Implementation Checklist

SARIF producer implementations MUST:

- [ ] Map OPA status to SARIF result.level per table above
- [ ] Use requirement.uid for rule.id (stability requirement)
- [ ] Map evidence code_span to physicalLocation with region
- [ ] Include all required property bag fields
- [ ] Construct clear, actionable result messages from decision.reasons
- [ ] Populate tool.driver with OPA bundle metadata
- [ ] Validate output against SARIF v2.1.0 schema
- [ ] Omit not_applicable results from output
- [ ] Add triage=needed property for inconclusive/blocked results
- [ ] Generate unique evaluation_id and link to decision log

## Examples

### Example 1: Failed Requirement

**OPA Decision**:
```json
{
  "status": "fail",
  "score": 0.4,
  "confidence": 0.85,
  "criteria": [
    {
      "id": "AC-1",
      "status": "fail",
      "weight": 3,
      "message": "Missing authentication on admin endpoints",
      "evidence": [0, 1]
    }
  ],
  "reasons": ["Authentication not enforced on administrative endpoints"],
  "policy": {
    "bundle": "org/cyber",
    "revision": "2026.01",
    "hash": "sha256:abc123..."
  }
}
```

**SARIF Result**:
```json
{
  "ruleId": "01HZQK9X7P8RJWV4GY5C2N3M6S",
  "level": "error",
  "message": {
    "text": "Authentication not enforced on administrative endpoints (Score: 0.40, Confidence: 0.85)"
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": "src/admin/routes.py",
          "uriBaseId": "SRCROOT"
        },
        "region": {
          "startLine": 15,
          "endLine": 28
        }
      }
    }
  ],
  "properties": {
    "requirement_uid": "01HZQK9X7P8RJWV4GY5C2N3M6S",
    "requirement_key": "CYBER-AC-001",
    "subtypes": ["CYBER", "ACCESS_CONTROL"],
    "policy_baseline_version": "2026.01",
    "opa_policy_hash": "sha256:abc123...",
    "agent_version": "1.2.0",
    "evaluation_id": "01HZQM1X8Q9SJXW5HZ6D3O4N7T",
    "timestamp": "2026-01-31T12:34:56Z",
    "opa_score": 0.4,
    "opa_confidence": 0.85
  }
}
```

### Example 2: Conditional Pass (Warning)

**OPA Decision**:
```json
{
  "status": "conditional_pass",
  "score": 0.7,
  "confidence": 0.9,
  "reasons": ["TLS enabled but version 1.2 used; recommend upgrading to TLS 1.3"],
  "policy": {
    "bundle": "org/cyber",
    "revision": "2026.01",
    "hash": "sha256:def456..."
  }
}
```

**SARIF Result**:
```json
{
  "ruleId": "01HZQK9X7P8RJWV4GY5C2N3M6T",
  "level": "warning",
  "message": {
    "text": "TLS enabled but version 1.2 used; recommend upgrading to TLS 1.3 (Score: 0.70, Confidence: 0.90)"
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": "config/nginx.conf",
          "uriBaseId": "SRCROOT"
        },
        "region": {
          "startLine": 42,
          "endLine": 42
        }
      }
    }
  ],
  "properties": {
    "requirement_uid": "01HZQK9X7P8RJWV4GY5C2N3M6T",
    "requirement_key": "CYBER-TLS-002",
    "subtypes": ["CYBER", "ENCRYPTION"],
    "policy_baseline_version": "2026.01",
    "opa_policy_hash": "sha256:def456...",
    "agent_version": "1.2.0",
    "evaluation_id": "01HZQM1X8Q9SJXW5HZ6D3O4N7U",
    "timestamp": "2026-01-31T12:34:57Z",
    "opa_score": 0.7,
    "opa_confidence": 0.9
  }
}
```

### Example 3: Inconclusive Result

**OPA Decision**:
```json
{
  "status": "inconclusive",
  "score": 0.0,
  "confidence": 0.3,
  "reasons": ["Insufficient evidence to evaluate requirement"],
  "policy": {
    "bundle": "org/cyber",
    "revision": "2026.01",
    "hash": "sha256:ghi789..."
  }
}
```

**SARIF Result**:
```json
{
  "ruleId": "01HZQK9X7P8RJWV4GY5C2N3M6U",
  "level": "warning",
  "message": {
    "text": "Insufficient evidence to evaluate requirement. Manual review required. (Score: 0.00, Confidence: 0.30)"
  },
  "properties": {
    "requirement_uid": "01HZQK9X7P8RJWV4GY5C2N3M6U",
    "requirement_key": "CYBER-LOG-003",
    "subtypes": ["CYBER", "AUDIT"],
    "policy_baseline_version": "2026.01",
    "opa_policy_hash": "sha256:ghi789...",
    "agent_version": "1.2.0",
    "evaluation_id": "01HZQM1X8Q9SJXW5HZ6D3O4N7V",
    "timestamp": "2026-01-31T12:34:58Z",
    "triage": "needed",
    "opa_score": 0.0,
    "opa_confidence": 0.3
  }
}
```

## References

- SARIF v2.1.0 Specification: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
- SARIF JSON Schema: https://json.schemastore.org/sarif-2.1.0.json
- ReqIF-OPA-SARIF requirement schema: `schemas/requirement-record.schema.json`
- OPA output schema: `schemas/opa-output.schema.json`
- Agent facts schema: `schemas/agent-facts.schema.json`
