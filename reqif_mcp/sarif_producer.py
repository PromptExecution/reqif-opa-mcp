"""SARIF producer module for compliance gate reporting.

This module transforms OPA policy evaluation decisions into SARIF v2.1.0 reports
following the normative mapping rules defined in docs/sarif-mapping.md.

Key responsibilities:
- Map OPA status to SARIF result.level
- Create SARIF rules from requirement records
- Map evidence code_span to physicalLocation
- Generate SARIF run objects with tool metadata
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from returns.result import Failure, Result, Success
from ulid import ULID


def create_sarif_rule(requirement: dict[str, Any]) -> dict[str, Any]:
    """Create SARIF rule object from requirement record.

    Maps requirement to SARIF rule following these conventions:
    - requirement.uid → rule.id (MUST be stable)
    - requirement.key → rule.name
    - requirement.text → rule.fullDescription.text
    - requirement.subtypes → rule.properties.subtypes

    Args:
        requirement: Requirement record conforming to reqif-mcp/1 schema

    Returns:
        SARIF rule object
    """
    return {
        "id": requirement["uid"],
        "name": requirement.get("key", requirement["uid"]),
        "fullDescription": {
            "text": requirement["text"]
        },
        "properties": {
            "subtypes": requirement.get("subtypes", []),
            "policy_baseline_version": requirement.get("policy_baseline", {}).get("version", "unknown"),
        }
    }


def _map_status_to_level(status: str) -> str | None:
    """Map OPA status to SARIF result.level.

    Mapping per docs/sarif-mapping.md:
    - pass → None (omit result)
    - fail → error
    - conditional_pass → warning
    - inconclusive → warning (with triage=needed)
    - blocked → warning (with triage=needed)
    - not_applicable → None (omit result)
    - waived → note (optional)

    Args:
        status: OPA evaluation status

    Returns:
        SARIF level string or None if result should be omitted
    """
    mapping = {
        "pass": None,
        "fail": "error",
        "conditional_pass": "warning",
        "inconclusive": "warning",
        "blocked": "warning",
        "not_applicable": None,
        "waived": "note",
    }
    return mapping.get(status, None)


def _extract_evidence_locations(
    facts: dict[str, Any],
    criterion_evidence_indices: list[int] | None = None
) -> list[dict[str, Any]]:
    """Extract SARIF locations from agent facts evidence.

    Maps evidence with type=code_span to SARIF physicalLocation objects.
    Evidence URI normalization:
    - Strip repo://github.com/org/repo/ prefix
    - Extract relative path
    - Use uriBaseId=SRCROOT for source code

    Args:
        facts: Agent facts object conforming to facts/1 schema
        criterion_evidence_indices: Optional list of evidence array indices to include

    Returns:
        List of SARIF location objects
    """
    evidence_array = facts.get("evidence", [])
    if not evidence_array:
        return []

    # If criterion specifies evidence indices, filter to those
    if criterion_evidence_indices is not None:
        evidence_items = [evidence_array[i] for i in criterion_evidence_indices if i < len(evidence_array)]
    else:
        evidence_items = evidence_array

    locations = []
    for evidence in evidence_items:
        if evidence.get("type") != "code_span":
            continue

        uri = evidence.get("uri", "")
        # Normalize URI: strip repo:// prefix and extract relative path
        relative_uri = uri
        if uri.startswith("repo://"):
            # Extract path after repo://host/org/repo/
            parts = uri.split("/", 6)
            if len(parts) >= 7:
                relative_uri = parts[6]
            else:
                relative_uri = uri.replace("repo://", "")

        location = {
            "physicalLocation": {
                "artifactLocation": {
                    "uri": relative_uri,
                    "uriBaseId": "SRCROOT"
                }
            }
        }

        # Add region if line numbers present
        start_line = evidence.get("startLine")
        end_line = evidence.get("endLine")
        if start_line is not None:
            region: dict[str, Any] = {"startLine": start_line}
            if end_line is not None:
                region["endLine"] = end_line
            location["physicalLocation"]["region"] = region

        locations.append(location)

    return locations


def _construct_result_message(decision: dict[str, Any]) -> str:
    """Construct SARIF result message from OPA decision.

    Message construction rules per docs/sarif-mapping.md:
    1. Use decision.reasons[] if available (join with semicolon)
    2. Fall back to aggregated criteria messages
    3. Append score and confidence for context

    Args:
        decision: OPA evaluation decision output

    Returns:
        Human-readable message string
    """
    reasons = decision.get("reasons", [])
    if reasons:
        base_message = "; ".join(reasons)
    else:
        # Aggregate criteria messages
        criteria = decision.get("criteria", [])
        messages = [c.get("message", "") for c in criteria if c.get("message")]
        base_message = "; ".join(messages) if messages else "Evaluation completed"

    # Append score and confidence
    score = decision.get("score", 0.0)
    confidence = decision.get("confidence", 0.0)
    return f"{base_message} (Score: {score:.2f}, Confidence: {confidence:.2f})"


def create_sarif_result(
    requirement: dict[str, Any],
    decision: dict[str, Any],
    facts: dict[str, Any],
    evaluation_id: str,
) -> dict[str, Any] | None:
    """Create SARIF result object from OPA decision.

    Maps OPA decision to SARIF result following docs/sarif-mapping.md:
    - Maps status to level (pass/not_applicable → omit result)
    - Constructs message from decision.reasons[]
    - Maps evidence to locations
    - Includes required property bag fields

    Args:
        requirement: Requirement record conforming to reqif-mcp/1 schema
        decision: OPA evaluation decision output
        facts: Agent facts object conforming to facts/1 schema
        evaluation_id: Unique evaluation identifier (ULID)

    Returns:
        SARIF result object or None if result should be omitted
    """
    status = decision.get("status", "inconclusive")
    level = _map_status_to_level(status)

    # Omit results for pass and not_applicable
    if level is None:
        return None

    # Extract locations from evidence
    locations = _extract_evidence_locations(facts)

    # Construct result message
    message_text = _construct_result_message(decision)

    # Build property bag with required fields
    properties: dict[str, Any] = {
        "requirement_uid": requirement.get("uid", "unknown"),
        "requirement_key": requirement.get("key", "unknown"),
        "subtypes": requirement.get("subtypes", []),
        "policy_baseline_version": requirement.get("policy_baseline", {}).get("version", "unknown"),
        "opa_policy_hash": decision.get("policy", {}).get("hash", "unknown"),
        "agent_version": facts.get("agent", {}).get("version", "unknown"),
        "evaluation_id": evaluation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Add optional properties
    if status in ["inconclusive", "blocked"]:
        properties["triage"] = "needed"

    properties["opa_score"] = decision.get("score", 0.0)
    properties["opa_confidence"] = decision.get("confidence", 0.0)

    # Add target information if available
    target = facts.get("target", {})
    if target.get("repo"):
        properties["target_repo"] = target["repo"]
    if target.get("commit"):
        properties["target_commit"] = target["commit"]

    # Build result object
    result: dict[str, Any] = {
        "ruleId": requirement["uid"],
        "level": level,
        "message": {
            "text": message_text
        },
        "properties": properties
    }

    # Add locations if available
    if locations:
        result["locations"] = locations

    return result


def generate_sarif_report(
    requirement: dict[str, Any],
    decision: dict[str, Any],
    facts: dict[str, Any],
    evaluation_id: str | None = None,
) -> dict[str, Any]:
    """Generate SARIF v2.1.0 report from OPA evaluation.

    Creates complete SARIF run object with:
    - Tool driver metadata from OPA bundle
    - SARIF rule from requirement
    - SARIF result from decision (if not pass/not_applicable)
    - Run-level properties with policy metadata

    Args:
        requirement: Requirement record conforming to reqif-mcp/1 schema
        decision: OPA evaluation decision output
        facts: Agent facts object conforming to facts/1 schema
        evaluation_id: Optional evaluation identifier (generates ULID if not provided)

    Returns:
        SARIF v2.1.0 report object
    """
    # Generate evaluation ID if not provided
    if evaluation_id is None:
        evaluation_id = str(ULID())

    # Create SARIF rule from requirement
    rule = create_sarif_rule(requirement)

    # Create SARIF result from decision
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Extract policy metadata
    policy = decision.get("policy", {})
    bundle_id = policy.get("bundle", "unknown")
    bundle_revision = policy.get("revision", "unknown")
    bundle_hash = policy.get("hash", "unknown")

    # Build SARIF run object
    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": bundle_id,
                "version": bundle_revision,
                "informationUri": "https://github.com/org/opa-bundles",
                "rules": [rule]
            }
        },
        "results": [result] if result is not None else [],
        "properties": {
            "policy_bundle": bundle_id,
            "policy_revision": bundle_revision,
            "policy_hash": bundle_hash,
            "evaluation_time": datetime.now(timezone.utc).isoformat(),
        }
    }

    # Build complete SARIF report
    sarif_report = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [run]
    }

    return sarif_report


def write_sarif_file(
    sarif_object: dict[str, Any],
    output_path: str | Path,
) -> Result[str, Exception]:
    """Write SARIF JSON object to file.

    Creates parent directories if needed and writes pretty-printed JSON.
    Returns the absolute path of the written file on success.

    Args:
        sarif_object: SARIF v2.1.0 report object to write
        output_path: File path to write to (string or Path)

    Returns:
        Result[str, Exception]: Success with absolute file path, or Failure with exception
    """
    try:
        # Convert to Path object
        file_path = Path(output_path)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write pretty-printed JSON
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(sarif_object, f, indent=2, ensure_ascii=False)

        # Return absolute path
        return Success(str(file_path.absolute()))

    except Exception as e:
        return Failure(e)
