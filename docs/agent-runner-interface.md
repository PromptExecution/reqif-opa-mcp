# Agent Runner Interface

## Overview

This document defines the interface contract for agent runners in the ReqIF-OPA-SARIF compliance gate system. Agents are responsible for extracting semantic facts from code artifacts and producing structured evidence - they NEVER make compliance decisions directly. All compliance decisions are made by OPA policies.

## Core Principle

**Agents produce facts; OPA makes decisions.**

Agents analyze code, build artifacts, and other inputs to extract typed facts and evidence pointers. The OPA policy engine evaluates these facts against requirement rubrics to produce deterministic compliance decisions.

## Interface Definition

### Function Signature

```python
def run_agent(
    subtype: str,
    artifacts_path: str | Path,
    requirement_context: dict[str, Any]
) -> Result[dict[str, Any], Exception]:
    """
    Run an agent to extract facts from artifacts for a specific requirement subtype.

    Args:
        subtype: Requirement subtype (e.g., "CYBER", "ACCESS_CONTROL", "DATA_PRIVACY")
        artifacts_path: Path to directory containing build artifacts, source code, or analysis targets
        requirement_context: Context object containing requirement metadata and evaluation parameters

    Returns:
        Result[dict, Exception]: Success containing facts/1 schema object, or Failure with error
    """
```

### Input Parameters

#### `subtype: str`
- **Description**: The requirement subtype that determines which analysis to perform
- **Format**: String value matching one of the requirement subtypes (e.g., "CYBER", "ACCESS_CONTROL", "DATA_PRIVACY", "PERFORMANCE")
- **Purpose**: Allows agents to specialize their analysis based on the domain
- **Examples**:
  - `"CYBER"` - Security and cryptography analysis
  - `"ACCESS_CONTROL"` - Authentication and authorization checks
  - `"DATA_PRIVACY"` - PII handling and data protection analysis
  - `"PERFORMANCE"` - Performance metrics and benchmarking

#### `artifacts_path: str | Path`
- **Description**: Filesystem path to the directory containing artifacts to analyze
- **Format**: Absolute or relative path (supports both string and pathlib.Path)
- **Contents**: May include:
  - Source code files
  - Build outputs (binaries, libraries)
  - Configuration files
  - Test results
  - Dependency manifests (e.g., package.json, requirements.txt, Cargo.toml)
  - SBOM files (Software Bill of Materials)
  - Static analysis reports
- **Purpose**: Provides the agent with all necessary artifacts for analysis
- **Example**: `/workspace/build/artifacts/` or `./target/release/`

#### `requirement_context: dict[str, Any]`
- **Description**: Context object providing requirement metadata and evaluation parameters
- **Format**: Dictionary with flexible structure (additionalProperties allowed)
- **Required Fields**:
  - `target`: Target metadata (repo, commit, build identifiers)
    - `repo`: str - Repository identifier
    - `commit`: str - Git commit hash
    - `build`: str - Build identifier or version
- **Optional Fields**:
  - `requirement_uid`: str - UID of the requirement being evaluated (for context)
  - `requirement_key`: str - Human-readable key (e.g., "CYBER-AC-001")
  - `requirement_text`: str - Full requirement statement
  - `policy_baseline`: dict - Policy baseline metadata (id, version, hash)
  - `rubric_hint`: str - Suggested OPA package for this requirement
  - `agent_config`: dict - Agent-specific configuration parameters
- **Purpose**: Provides agents with context about what they're evaluating and for whom
- **Example**:
  ```json
  {
    "target": {
      "repo": "github.com/org/project",
      "commit": "a1b2c3d4",
      "build": "v2.3.1-rc.5"
    },
    "requirement_uid": "req-cyber-001",
    "requirement_key": "CYBER-AC-001",
    "rubric_hint": "cyber.access_control.v3",
    "agent_config": {
      "severity_threshold": "medium",
      "include_dependencies": true
    }
  }
  ```

### Output Format

Agents MUST return a `Result[dict, Exception]` object using the `returns` module for Rust-style error handling.

#### Success Case: `Success(facts_object)`

The facts object MUST conform to the **facts/1 schema** (see `schemas/agent-facts.schema.json`).

**Structure:**
```json
{
  "target": {
    "repo": "github.com/org/project",
    "commit": "a1b2c3d4",
    "build": "v2.3.1-rc.5"
  },
  "facts": {
    "uses_crypto_library": true,
    "crypto_libraries": ["openssl", "libsodium"],
    "inputs_validated": [
      {"path": "src/auth.rs", "line": 44, "kind": "missing"}
    ],
    "access_control_implemented": true,
    "authentication_methods": ["oauth2", "api_key"]
  },
  "evidence": [
    {
      "type": "code_span",
      "uri": "repo://github.com/org/project/src/auth.rs",
      "startLine": 40,
      "endLine": 55
    },
    {
      "type": "artifact",
      "uri": "artifact://sbom.cdx.json",
      "hash": "sha256:abc123..."
    }
  ],
  "agent": {
    "name": "cyber-security-agent",
    "version": "1.2.3",
    "rubric_hint": "cyber.access_control.v3"
  }
}
```

**Required Fields:**
- `target`: Object with repo, commit, build fields
- `facts`: Object with arbitrary boolean, string, number, array, or object properties
- `evidence`: Array of evidence items (may be empty)
- `agent`: Object with name and version; rubric_hint is optional

**Evidence Types:**
- `code_span`: Source code location
  - Required: type, uri, startLine, endLine
- `artifact`: Build artifact, SBOM, or external file
  - Required: type, uri
  - Optional: hash (for content verification)
- `log`: Log file or trace
  - Required: type, uri
- `metric`: Performance or quality metric
  - Required: type, uri

**Evidence URIs:**
Use stable, addressable URIs:
- `repo://github.com/org/project/path/to/file.ext` - Source code in repository
- `artifact://filename.ext` - Build artifact in artifacts_path
- `file:///absolute/path/to/file` - Filesystem path
- `http://example.com/resource` - External resource

#### Failure Case: `Failure(exception)`

Return a `Failure` containing an exception object when:
- The agent cannot complete its analysis
- Required files or artifacts are missing
- The artifacts_path is invalid or inaccessible
- Analysis tools fail (e.g., linters, static analyzers)
- The subtype is not supported by this agent

**Example:**
```python
from returns.result import Failure

# Missing artifacts
if not artifacts_path.exists():
    return Failure(ValueError(f"Artifacts path not found: {artifacts_path}"))

# Unsupported subtype
if subtype not in SUPPORTED_SUBTYPES:
    return Failure(ValueError(f"Unsupported subtype: {subtype}"))

# Analysis tool failure
try:
    result = subprocess.run([...], capture_output=True, check=True)
except subprocess.CalledProcessError as e:
    return Failure(RuntimeError(f"Analysis tool failed: {e.stderr}"))
```

### Error Handling

**Critical Rules:**
1. **NEVER throw exceptions** - Always return `Result[dict, Exception]`
2. **Use Failure for all errors** - Return `Failure(exception)` instead of raising
3. **Provide clear error messages** - Include context about what failed and why
4. **Log errors internally** - Agent may log to stderr, but must still return Failure
5. **Partial results are failures** - If analysis is incomplete, return Failure (don't return partial facts)

**Example Error Handling:**
```python
from returns.result import Result, Success, Failure
from pathlib import Path
import logging

def run_agent(
    subtype: str,
    artifacts_path: str | Path,
    requirement_context: dict[str, Any]
) -> Result[dict[str, Any], Exception]:
    try:
        # Validate inputs
        path = Path(artifacts_path)
        if not path.exists():
            return Failure(ValueError(f"Artifacts path does not exist: {path}"))

        if not path.is_dir():
            return Failure(ValueError(f"Artifacts path is not a directory: {path}"))

        # Extract target from context
        target = requirement_context.get("target")
        if not target:
            return Failure(ValueError("requirement_context missing 'target' field"))

        # Perform analysis
        facts = analyze_artifacts(path, subtype)
        evidence = extract_evidence(path, facts)

        # Build facts object
        facts_object = {
            "target": target,
            "facts": facts,
            "evidence": evidence,
            "agent": {
                "name": "example-agent",
                "version": "1.0.0",
                "rubric_hint": f"{subtype.lower()}.v1"
            }
        }

        return Success(facts_object)

    except Exception as e:
        # Catch unexpected errors and return Failure
        logging.error(f"Agent failed: {e}", exc_info=True)
        return Failure(RuntimeError(f"Agent execution failed: {e}"))
```

## Implementation Guidelines

### Agent Structure

Agents should be implemented as:
1. **Standalone scripts** - Can be invoked via command line
2. **Python modules** - Importable and callable from other code
3. **Configurable** - Accept configuration via CLI args or environment variables

### Agent Responsibilities

**Agents MUST:**
- Extract facts from artifacts (booleans, strings, numbers, arrays, objects)
- Provide evidence pointers (code spans, artifacts, logs)
- Return facts/1 conformant output
- Handle errors gracefully (return Failure, not throw)
- Be deterministic (same inputs → same outputs)
- Be idempotent (can run multiple times safely)

**Agents MUST NOT:**
- Make pass/fail decisions (that's OPA's job)
- Return compliance status (pass, fail, etc.)
- Interpret policy requirements directly
- Modify artifacts or source code
- Make assumptions about policy thresholds

### Fact Naming Conventions

Use clear, semantic fact names:
- **Booleans**: `uses_crypto_library`, `authentication_required`, `logging_enabled`
- **Strings**: `primary_language`, `framework_version`, `license_type`
- **Numbers**: `code_coverage_pct`, `cyclomatic_complexity`, `dependency_count`
- **Arrays**: `crypto_libraries`, `exposed_endpoints`, `validation_failures`
- **Objects**: `scan_results`, `dependency_tree`, `metrics`

### Evidence Best Practices

- **Always provide evidence** for facts that matter
- **Use code_span** for source code locations (with line numbers)
- **Use artifact** for SBOMs, dependency manifests, scan reports
- **Include hashes** for artifacts to ensure integrity
- **Use stable URIs** that can be resolved later

### Testing Agents

Agents should include:
1. **Unit tests** - Test fact extraction logic
2. **Integration tests** - Test against sample artifacts
3. **Schema validation tests** - Verify output conforms to facts/1
4. **Error handling tests** - Verify Failure returns for error cases

## Examples

### Example 1: CYBER Subtype Agent

```python
from returns.result import Result, Success, Failure
from pathlib import Path
import json

def run_agent(
    subtype: str,
    artifacts_path: str | Path,
    requirement_context: dict[str, Any]
) -> Result[dict[str, Any], Exception]:
    """CYBER subtype agent - analyzes cryptography and security."""

    if subtype != "CYBER":
        return Failure(ValueError(f"Unsupported subtype: {subtype}"))

    path = Path(artifacts_path)
    if not path.exists():
        return Failure(ValueError(f"Path not found: {path}"))

    # Extract facts
    uses_crypto = check_crypto_usage(path)
    crypto_libs = find_crypto_libraries(path)

    # Gather evidence
    evidence = []
    for lib_location in crypto_libs:
        evidence.append({
            "type": "code_span",
            "uri": f"repo://{lib_location['file']}",
            "startLine": lib_location['line'],
            "endLine": lib_location['line']
        })

    # Build output
    facts_object = {
        "target": requirement_context["target"],
        "facts": {
            "uses_crypto_library": uses_crypto,
            "crypto_libraries": [lib["name"] for lib in crypto_libs],
            "crypto_count": len(crypto_libs)
        },
        "evidence": evidence,
        "agent": {
            "name": "cyber-agent",
            "version": "1.0.0",
            "rubric_hint": "cyber.access_control.v3"
        }
    }

    return Success(facts_object)
```

### Example 2: ACCESS_CONTROL Subtype Agent

```python
def run_agent(
    subtype: str,
    artifacts_path: str | Path,
    requirement_context: dict[str, Any]
) -> Result[dict[str, Any], Exception]:
    """ACCESS_CONTROL subtype agent - analyzes authentication/authorization."""

    if subtype != "ACCESS_CONTROL":
        return Failure(ValueError(f"Unsupported subtype: {subtype}"))

    path = Path(artifacts_path)

    # Analyze authentication
    auth_methods = detect_authentication_methods(path)
    authz_enforced = check_authorization_enforcement(path)

    # Gather evidence
    evidence = []
    if authz_enforced:
        evidence.append({
            "type": "code_span",
            "uri": "repo://src/middleware/authz.rs",
            "startLine": 25,
            "endLine": 50
        })

    facts_object = {
        "target": requirement_context["target"],
        "facts": {
            "authentication_methods": auth_methods,
            "authorization_enforced": authz_enforced,
            "rbac_implemented": "rbac" in auth_methods
        },
        "evidence": evidence,
        "agent": {
            "name": "access-control-agent",
            "version": "2.1.0",
            "rubric_hint": "cyber.access_control.v3"
        }
    }

    return Success(facts_object)
```

## Integration with System

### Workflow

1. **CI Pipeline** queries requirements via `reqif.query` tool
2. **Agent Runner** invokes appropriate agent based on requirement subtype
3. **Agent** analyzes artifacts and returns facts/1 object
4. **OPA Evaluator** combines requirement + facts → evaluation
5. **SARIF Producer** generates SARIF report from evaluation
6. **Evidence Store** records verification event

### Agent Selection

Agents can be selected by:
- **Subtype mapping** - Map requirement subtype to agent (e.g., CYBER → cyber-agent)
- **Rubric hint** - Use requirement.rubrics[].package to select agent
- **Configuration** - Use agent_config in requirement_context

### Agent Registry (Future)

In production, consider an agent registry:
```json
{
  "agents": [
    {
      "name": "cyber-agent",
      "subtypes": ["CYBER", "CRYPTOGRAPHY"],
      "command": "python agents/cyber_agent.py",
      "version": "1.0.0"
    },
    {
      "name": "access-control-agent",
      "subtypes": ["ACCESS_CONTROL", "AUTHENTICATION"],
      "command": "python agents/access_control_agent.py",
      "version": "2.1.0"
    }
  ]
}
```

## See Also

- [Agent Facts Schema](../schemas/agent-facts.schema.json) - facts/1 data contract
- [OPA Input Schema](../schemas/opa-input.schema.json) - How facts are passed to OPA
- [SARIF Mapping](./sarif-mapping.md) - How decisions become SARIF reports
- [Evidence Store](./evidence-store.md) - How evidence is persisted
