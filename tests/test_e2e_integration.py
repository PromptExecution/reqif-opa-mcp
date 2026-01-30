"""
End-to-end integration test for ReqIF-OPA-SARIF compliance gate.

This test exercises all major components:
- ReqIF parsing and normalization
- Stub agent fact extraction
- OPA policy evaluation
- SARIF report generation
- Verification event writing
- SARIF schema validation
- Traceability chain validation
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from returns.result import Success

# Import all required modules
from reqif_mcp import (
    evaluate_requirement,
    generate_sarif_report,
    normalize_reqif,
    parse_reqif_xml,
    validate_sarif,
    validate_verification_event_from_schema_file,
    write_sarif_file,
)


# Test fixtures path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_REQIF = FIXTURES_DIR / "sample_baseline.reqif"
STUB_AGENT = Path(__file__).parent.parent / "agents" / "stub_agent.py"
OPA_BUNDLE = Path(__file__).parent.parent / "opa-bundles" / "example"
EVIDENCE_STORE = Path(__file__).parent.parent / "evidence_store"


# Check if OPA is available
OPA_AVAILABLE = shutil.which("opa") is not None


@pytest.mark.skipif(not OPA_AVAILABLE, reason="OPA binary not found in PATH")
def test_e2e_compliance_gate_integration() -> None:
    """
    End-to-end integration test: ReqIF baseline → agent facts → OPA → SARIF → verification event.

    Tests the complete compliance gate flow:
    1. Parse sample ReqIF baseline with 5 test requirements
    2. Invoke stub agent to produce facts for each requirement subtype
    3. Evaluate requirements with OPA using example bundle
    4. Generate SARIF reports
    5. Write verification events to evidence store
    6. Validate SARIF output against schema
    7. Assert trace links present (requirement uid in event and SARIF)
    """

    # ============================================================================
    # STEP 1: Parse sample ReqIF baseline with 5 test requirements
    # ============================================================================

    assert SAMPLE_REQIF.exists(), f"Sample ReqIF file not found: {SAMPLE_REQIF}"

    # Parse ReqIF XML
    parse_result = parse_reqif_xml(SAMPLE_REQIF)
    assert isinstance(parse_result, Success), f"Failed to parse ReqIF: {parse_result}"
    reqif_data = parse_result.unwrap()

    # Validate parsed data structure
    assert "spec_objects" in reqif_data
    assert len(reqif_data["spec_objects"]) == 5, "Expected 5 requirements in sample baseline"

    # Normalize ReqIF data into requirement records
    normalize_result = normalize_reqif(
        reqif_data,
        policy_baseline_id="TEST-BASELINE-2026",
        policy_baseline_version="2026.01"
    )
    assert isinstance(normalize_result, Success), f"Failed to normalize ReqIF: {normalize_result}"
    requirements = normalize_result.unwrap()

    # Validate normalized requirements
    assert len(requirements) == 5, "Expected 5 normalized requirements"

    # Check that all requirements have required fields
    for req in requirements:
        assert "uid" in req
        assert "key" in req
        assert "subtypes" in req
        assert "status" in req
        assert "policy_baseline" in req
        assert "rubrics" in req
        assert "text" in req

    # Verify specific requirements are present
    req_keys = {req["key"] for req in requirements}
    expected_keys = {
        "CYBER-ENC-001",
        "AC-AUTH-001",
        "DP-PII-001",
        "AUDIT-LOG-001",
        "CYBER-AC-MFA-001"
    }
    assert req_keys == expected_keys, f"Expected keys {expected_keys}, got {req_keys}"

    # ============================================================================
    # STEP 2: Invoke stub agent to produce facts for target
    # ============================================================================

    assert STUB_AGENT.exists(), f"Stub agent not found: {STUB_AGENT}"

    # Run stub agent for CYBER subtype
    result = subprocess.run(
        [sys.executable, str(STUB_AGENT), "--subtype", "CYBER"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert result.returncode == 0, f"Stub agent failed: {result.stderr}"

    # Parse agent facts output
    agent_facts = json.loads(result.stdout)

    # Validate agent facts structure
    assert "target" in agent_facts
    assert "facts" in agent_facts
    assert "evidence" in agent_facts
    assert "agent" in agent_facts

    # Validate agent metadata
    assert agent_facts["agent"]["name"] == "stub-agent"
    assert agent_facts["agent"]["version"] == "0.1.0"

    # Validate CYBER-specific facts
    assert agent_facts["facts"]["uses_crypto_library"] is True
    assert "crypto_algorithms" in agent_facts["facts"]

    # Validate evidence pointers
    assert len(agent_facts["evidence"]) > 0
    for evidence in agent_facts["evidence"]:
        assert "type" in evidence
        assert "uri" in evidence

    # ============================================================================
    # STEP 3: Invoke OPA evaluation with example bundle
    # ============================================================================

    assert OPA_BUNDLE.exists(), f"OPA bundle not found: {OPA_BUNDLE}"

    # Find a CYBER requirement to evaluate
    cyber_req = next(req for req in requirements if "CYBER" in req["subtypes"])

    # Evaluate requirement with OPA
    eval_result = evaluate_requirement(
        requirement=cyber_req,
        facts=agent_facts,
        bundle_path=str(OPA_BUNDLE),
        context={"test_mode": True},
        enable_decision_logging=True
    )

    assert isinstance(eval_result, Success), f"OPA evaluation failed: {eval_result}"
    decision = eval_result.unwrap()

    # Validate OPA decision structure
    assert "status" in decision
    assert decision["status"] in [
        "pass", "fail", "conditional_pass",
        "inconclusive", "not_applicable", "blocked", "waived"
    ]
    assert "score" in decision
    assert 0.0 <= decision["score"] <= 1.0
    assert "confidence" in decision
    assert 0.0 <= decision["confidence"] <= 1.0
    assert "criteria" in decision
    assert isinstance(decision["criteria"], list)
    assert "reasons" in decision
    assert isinstance(decision["reasons"], list)
    assert "policy" in decision

    # Validate policy provenance
    assert "bundle" in decision["policy"]
    assert "revision" in decision["policy"]
    assert "hash" in decision["policy"]

    # ============================================================================
    # STEP 4: Generate SARIF report
    # ============================================================================

    sarif_report = generate_sarif_report(
        requirement=cyber_req,
        decision=decision,
        facts=agent_facts
    )

    # Validate SARIF report structure
    assert "$schema" in sarif_report
    assert sarif_report["version"] == "2.1.0"
    assert "runs" in sarif_report
    assert len(sarif_report["runs"]) == 1

    run = sarif_report["runs"][0]
    assert "tool" in run
    assert "results" in run

    # Validate tool metadata
    assert "driver" in run["tool"]
    assert "name" in run["tool"]["driver"]

    # Check if results were generated (depends on decision status)
    # fail → error, conditional_pass → warning, pass/not_applicable → omit
    if decision["status"] in ["fail", "conditional_pass", "inconclusive", "blocked"]:
        assert len(run["results"]) > 0, "Expected SARIF results for non-pass status"

        # Validate result structure
        result_item = run["results"][0]
        assert "ruleId" in result_item
        assert result_item["ruleId"] == cyber_req["uid"], "Rule ID must match requirement UID"
        assert "level" in result_item
        assert "message" in result_item
        assert "properties" in result_item

        # Validate required property bag fields
        props = result_item["properties"]
        assert "requirement_uid" in props
        assert "requirement_key" in props
        assert "subtypes" in props
        assert "policy_baseline_version" in props
        assert "opa_policy_hash" in props
        assert "agent_version" in props
        assert "evaluation_id" in props
        assert "timestamp" in props

        # Validate trace link: requirement UID matches
        assert props["requirement_uid"] == cyber_req["uid"]

    # ============================================================================
    # STEP 5: Write SARIF file
    # ============================================================================

    sarif_output_path = EVIDENCE_STORE / "sarif" / "test_e2e.sarif"
    write_result = write_sarif_file(sarif_report, str(sarif_output_path))
    assert isinstance(write_result, Success), f"Failed to write SARIF file: {write_result}"

    assert sarif_output_path.exists(), "SARIF file was not created"

    # Verify file contents
    with open(sarif_output_path, "r") as f:
        saved_sarif = json.load(f)
    assert saved_sarif == sarif_report, "Saved SARIF does not match generated report"

    # ============================================================================
    # STEP 6: Validate SARIF output against schema
    # ============================================================================

    validation_result = validate_sarif(sarif_report, None)
    assert isinstance(validation_result, Success), f"SARIF validation failed: {validation_result}"

    validation_report = validation_result.unwrap()
    assert validation_report.valid is True, f"SARIF schema validation failed: {validation_report.errors}"

    # ============================================================================
    # STEP 7: Write verification event to store
    # ============================================================================

    # Create verification event
    verification_event: dict[str, Any] = {
        "requirement_uid": cyber_req["uid"],
        "target": agent_facts["target"],
        "decision": {
            "status": decision["status"],
            "score": decision["score"],
            "confidence": decision["confidence"]
        },
        "sarif_ref": "test_e2e.sarif"
    }

    # Validate event against schema
    schema_path = Path(__file__).parent.parent / "schemas" / "verification-event.schema.json"
    event_validation = validate_verification_event_from_schema_file(verification_event, schema_path)
    assert isinstance(event_validation, Success), f"Event validation failed: {event_validation}"
    event_val_result = event_validation.unwrap()
    assert event_val_result["valid"] is True, f"Event schema validation failed: {event_val_result['errors']}"

    # Write event to JSONL log
    event_log_path = EVIDENCE_STORE / "events" / "test_verifications.jsonl"
    event_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Auto-generate event_id and timestamp if not present
    from datetime import datetime, timezone
    from ulid import ULID

    if "event_id" not in verification_event:
        verification_event["event_id"] = str(ULID())
    if "timestamp" not in verification_event:
        verification_event["timestamp"] = datetime.now(timezone.utc).isoformat()

    with open(event_log_path, "a") as f:
        f.write(json.dumps(verification_event, ensure_ascii=False) + "\n")

    assert event_log_path.exists(), "Verification event log was not created"

    # ============================================================================
    # STEP 8: Assert trace links present
    # ============================================================================

    # Verify traceability chain: requirement uid appears in:
    # 1. Verification event
    assert verification_event["requirement_uid"] == cyber_req["uid"]

    # 2. SARIF report (if results were generated)
    if decision["status"] in ["fail", "conditional_pass", "inconclusive", "blocked"]:
        sarif_rule_ids = [result["ruleId"] for result in run["results"]]
        assert cyber_req["uid"] in sarif_rule_ids, "Requirement UID not found in SARIF rule IDs"

    # 3. Decision log (check that it was written)
    decision_log_path = EVIDENCE_STORE / "decision_logs" / "decisions.jsonl"
    assert decision_log_path.exists(), "Decision log was not created"

    # Read last decision log entry
    with open(decision_log_path, "r") as f:
        lines = f.readlines()
        assert len(lines) > 0, "Decision log is empty"
        last_entry = json.loads(lines[-1])
        assert last_entry["requirement"]["uid"] == cyber_req["uid"]

    # Verify all trace links use same requirement UID
    assert verification_event["requirement_uid"] == cyber_req["uid"]
    assert last_entry["requirement"]["uid"] == cyber_req["uid"]

    # Clean up test artifacts
    sarif_output_path.unlink(missing_ok=True)
    event_log_path.unlink(missing_ok=True)


@pytest.mark.skipif(not OPA_AVAILABLE, reason="OPA binary not found in PATH")
def test_e2e_multiple_requirements() -> None:
    """
    Test evaluating multiple requirements with different subtypes.

    This validates that the system can handle batch processing of requirements
    with different subtypes and generate appropriate SARIF results.
    """

    # Parse and normalize ReqIF baseline
    parse_result = parse_reqif_xml(SAMPLE_REQIF)
    assert isinstance(parse_result, Success)
    reqif_data = parse_result.unwrap()

    normalize_result = normalize_reqif(
        reqif_data,
        policy_baseline_id="TEST-BASELINE-2026",
        policy_baseline_version="2026.01"
    )
    assert isinstance(normalize_result, Success)
    requirements = normalize_result.unwrap()

    # Test each requirement with appropriate agent facts
    for req in requirements:
        # Get first subtype to determine which agent to run
        subtype = req["subtypes"][0]

        # Run stub agent for this subtype
        result = subprocess.run(
            [sys.executable, str(STUB_AGENT), "--subtype", subtype],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"Stub agent failed for {subtype}: {result.stderr}"
        agent_facts = json.loads(result.stdout)

        # Evaluate requirement
        eval_result = evaluate_requirement(
            requirement=req,
            facts=agent_facts,
            bundle_path=str(OPA_BUNDLE),
            context={"test_mode": True},
            enable_decision_logging=False  # Skip logging for batch test
        )

        # Should succeed for all requirements
        assert isinstance(eval_result, Success), f"Evaluation failed for {req['key']}: {eval_result}"
        decision = eval_result.unwrap()

        # Validate decision structure
        assert "status" in decision
        assert "score" in decision
        assert "criteria" in decision

        # Generate SARIF report
        sarif = generate_sarif_report(req, decision, agent_facts)

        # Validate SARIF structure
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1


def test_e2e_without_opa() -> None:
    """
    End-to-end test without requiring OPA installation.

    This test validates the full chain except OPA evaluation by using mock decision data:
    1. Parse sample ReqIF baseline
    2. Invoke stub agent
    3. Generate SARIF report with mock OPA decision
    4. Validate SARIF against schema
    5. Write verification event
    """

    # Parse ReqIF baseline
    parse_result = parse_reqif_xml(SAMPLE_REQIF)
    assert isinstance(parse_result, Success)
    reqif_data = parse_result.unwrap()

    normalize_result = normalize_reqif(
        reqif_data,
        policy_baseline_id="TEST-BASELINE-2026",
        policy_baseline_version="2026.01"
    )
    assert isinstance(normalize_result, Success)
    requirements = normalize_result.unwrap()
    assert len(requirements) == 5

    # Run stub agent
    result = subprocess.run(
        [sys.executable, str(STUB_AGENT), "--subtype", "CYBER"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert result.returncode == 0
    agent_facts = json.loads(result.stdout)

    # Create mock OPA decision
    cyber_req = next(req for req in requirements if "CYBER" in req["subtypes"])
    mock_decision: dict[str, Any] = {
        "status": "fail",
        "score": 0.6,
        "confidence": 0.8,
        "criteria": [
            {
                "id": "CRYPTO-1",
                "status": "pass",
                "weight": 3,
                "message": "Strong cryptographic algorithms detected",
                "evidence": [0, 1]
            },
            {
                "id": "CRYPTO-2",
                "status": "fail",
                "weight": 5,
                "message": "Weak encryption configuration found",
                "evidence": [2]
            }
        ],
        "reasons": [
            "Weak encryption configuration detected in src/crypto/config.py",
            "TLS version 1.1 is deprecated"
        ],
        "policy": {
            "bundle": "org/compliance",
            "revision": "2026.01",
            "hash": "sha256:abc123"
        }
    }

    # Generate SARIF report
    sarif_report = generate_sarif_report(cyber_req, mock_decision, agent_facts)

    # Validate SARIF structure
    assert sarif_report["version"] == "2.1.0"
    assert len(sarif_report["runs"]) == 1
    run = sarif_report["runs"][0]

    # Validate results were generated for fail status
    assert len(run["results"]) > 0
    result_item = run["results"][0]
    assert result_item["ruleId"] == cyber_req["uid"]
    assert result_item["level"] == "error"  # fail maps to error
    assert "properties" in result_item

    # Validate property bag
    props = result_item["properties"]
    assert props["requirement_uid"] == cyber_req["uid"]
    assert props["requirement_key"] == cyber_req["key"]
    assert "CYBER" in props["subtypes"]
    assert props["policy_baseline_version"] == "2026.01"
    assert "opa_policy_hash" in props
    assert "agent_version" in props

    # Validate SARIF against schema
    validation_result = validate_sarif(sarif_report, None)
    assert isinstance(validation_result, Success)
    validation_report = validation_result.unwrap()
    assert validation_report.valid is True

    # Write SARIF to file
    sarif_output_path = EVIDENCE_STORE / "sarif" / "test_e2e_no_opa.sarif"
    write_result = write_sarif_file(sarif_report, str(sarif_output_path))
    assert isinstance(write_result, Success)
    assert sarif_output_path.exists()

    # Create and validate verification event
    verification_event: dict[str, Any] = {
        "requirement_uid": cyber_req["uid"],
        "target": agent_facts["target"],
        "decision": {
            "status": mock_decision["status"],
            "score": mock_decision["score"],
            "confidence": mock_decision["confidence"]
        },
        "sarif_ref": "test_e2e_no_opa.sarif"
    }

    # Auto-generate event_id and timestamp
    from datetime import datetime, timezone
    from ulid import ULID

    verification_event["event_id"] = str(ULID())
    verification_event["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Validate event schema
    schema_path = Path(__file__).parent.parent / "schemas" / "verification-event.schema.json"
    event_validation = validate_verification_event_from_schema_file(verification_event, schema_path)
    assert isinstance(event_validation, Success)
    event_val_result = event_validation.unwrap()
    assert event_val_result["valid"] is True

    # Write verification event
    event_log_path = EVIDENCE_STORE / "events" / "test_verifications_no_opa.jsonl"
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(event_log_path, "a") as f:
        f.write(json.dumps(verification_event, ensure_ascii=False) + "\n")

    # Verify trace links
    assert verification_event["requirement_uid"] == cyber_req["uid"]
    assert result_item["ruleId"] == cyber_req["uid"]

    # Clean up test artifacts
    sarif_output_path.unlink(missing_ok=True)
    event_log_path.unlink(missing_ok=True)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
