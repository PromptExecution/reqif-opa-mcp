# ReqIF-OPA-MCP Compliance Gate

> Transform ReqIF requirements into deterministic OPA policy gates with SARIF reporting.

[![Docker](https://ghcr-badge.egpl.dev/promptexecution/reqif-opa-mcp/latest_tag?label=ghcr.io&trim=)](https://github.com/PromptExecution/reqif-opa-mcp/pkgs/container/reqif-opa-mcp)

## Overview

Standards-first compliance automation: ReqIF (requirements) → OPA (policy evaluation) → SARIF (portable reports).

**Core Stack:** ReqIF 1.2 · OPA · SARIF v2.1.0 · FastMCP 3.0

## Quick Start

```bash
# Install
just install

# Run server
just dev                    # STDIO mode
just serve                  # HTTP mode

# Docker
docker pull ghcr.io/promptexecution/reqif-opa-mcp:latest
docker run -p 8000:8000 ghcr.io/promptexecution/reqif-opa-mcp:latest
```

## Architecture

```mermaid
flowchart LR
  ReqIF[ReqIF XML] --> MCP[MCP Server]
  MCP --> Query[Query Requirements]
  Query --> Agent[Agent: Extract Facts]
  Agent --> OPA[OPA: Evaluate Policy]
  OPA --> SARIF[SARIF Report]
  SARIF --> Evidence[Evidence Store]
```

## Data Contracts

### Requirement (reqif-mcp/1)
```json
{
  "uid": "CYBER-AC-001",
  "key": "CYBER-AC-001",
  "subtypes": ["CYBER", "ACCESS_CONTROL"],
  "status": "active",
  "policy_baseline": {"id": "POL-2026.01", "version": "2026.01"},
  "rubrics": [{"engine": "opa", "package": "cyber.access_control.v3"}],
  "text": "Requirement statement",
  "attrs": {"severity": "high"}
}
```

### Agent Facts (facts/1)
```json
{
  "target": {"repo": "...", "commit": "..."},
  "facts": {
    "uses_crypto_library": true,
    "inputs_validated": [{"path": "src/x.rs", "line": 44}]
  },
  "evidence": [
    {"type": "code_span", "uri": "repo://...", "startLine": 40, "endLine": 55}
  ],
  "agent": {"name": "cyber-agent", "version": "1.0.0"}
}
```

### OPA Decision
```json
{
  "status": "pass|fail|conditional_pass|inconclusive",
  "score": 0.85,
  "confidence": 0.9,
  "criteria": [
    {"id": "AC-1", "status": "pass", "weight": 3, "message": "..."}
  ],
  "policy": {"bundle": "org/cyber", "hash": "..."}
}
```

### SARIF Mapping
- `fail` → `error`
- `conditional_pass` → `warning`
- `inconclusive` → `warning` + `triage=needed`
- `pass` / `not_applicable` → omit

## MCP Server Tools

```python
reqif.parse(xml_b64) -> handle
reqif.query(subtypes=[], baseline=id) -> requirements[]
reqif.write_verification(event) -> ok
```

**Resources:**
- `reqif://baseline/{id}` - Baseline metadata
- `reqif://requirement/{uid}` - Requirement details

## CI/CD Integration

```bash
# 1. Parse baseline
uv run python -m reqif_mcp --http &

# 2. Query requirements
curl http://localhost:8000/reqif.query -d '{"subtypes":["CYBER"]}'

# 3. Run agent
python agents/stub_agent.py > facts.json

# 4. Evaluate with OPA
opa eval -d opa-bundles/example -i input.json data.cyber.decision

# 5. Generate SARIF
python -m reqif_mcp.sarif_producer
```

See `.github/workflows/compliance-gate.yml` for full example.

## Development

```bash
just check              # lint + typecheck + test
just test               # Run tests
just docker-build       # Build image
```

See [RELEASE.md](RELEASE.md) for release workflow.

## Evidence Store

```
evidence_store/
├── events/             # JSONL event log (append-only)
├── sarif/              # SARIF reports
└── decision_logs/      # OPA decision logs
```

**Audit Trail:** Decision logs are immutable. Use external rotation (logrotate) for production.

## Gate Criteria

**Status:** `pass`, `fail`, `conditional_pass`, `inconclusive`, `blocked`, `not_applicable`, `waived`

**Metrics:**
- `score` ∈ [0,1] - Weighted rubric score
- `confidence` ∈ [0,1] - Evidence quality
- `severity` - Requirement criticality

**Gate Policies:**
- Block release if `fail` + `severity >= high`
- Require coverage threshold
- Allow `conditional_pass` for non-critical

## Standards

- **ReqIF 1.2** - Requirements interchange format
- **SARIF v2.1.0** - Static analysis results (OASIS standard)
- **OPA** - Policy-as-code evaluation
- **FastMCP 3.0** - MCP server with HTTP transport

## Agent Contract

Agents produce facts, never decisions. Output schema `facts/1`:

```python
{
  "target": {...},
  "facts": {...},
  "evidence": [...],
  "agent": {"name": "...", "version": "..."}
}
```

See [AGENTS.md](AGENTS.md) for development guidelines.

## License

Apache-2.0

## Documentation

- [CLAUDE.md](CLAUDE.md) - Architecture & design decisions
- [AGENTS.md](AGENTS.md) - Agent development guide
- [RELEASE.md](RELEASE.md) - Release process
