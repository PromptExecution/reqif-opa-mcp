"""Unit tests for SARIF mapping invariants.

Tests verify that the SARIF producer correctly maps OPA decisions to SARIF reports
according to the normative mapping rules defined in docs/sarif-mapping.md.

Key invariants tested:
- OPA fail status produces SARIF error result
- OPA pass status produces no result or note result
- OPA conditional_pass produces SARIF warning result
- rule.id matches requirement uid (stable)
- result.locations present when evidence has code spans
- property bag includes all required fields
"""


from reqif_mcp.sarif_producer import (
    _extract_evidence_locations,
    _map_status_to_level,
    create_sarif_result,
    create_sarif_rule,
    generate_sarif_report,
)


def test_opa_fail_status_produces_sarif_error_result() -> None:
    """Test that OPA fail status produces SARIF error result."""
    requirement = {
        "uid": "REQ-001",
        "key": "CYBER-AC-001",
        "text": "System must implement access control",
        "subtypes": ["CYBER", "ACCESS_CONTROL"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/cyber", "package": "cyber.access_control.v3", "rule": "decision"}],
    }

    decision = {
        "status": "fail",
        "score": 0.0,
        "confidence": 0.8,
        "criteria": [
            {"id": "CYBER-AC-1", "status": "fail", "weight": 3, "message": "Access control not implemented", "evidence": [0]},
        ],
        "reasons": ["Access control mechanisms missing"],
        "policy": {"bundle": "org/cyber", "revision": "2026.01.15", "hash": "def456"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"access_control_enabled": False},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/main.py", "startLine": 10, "endLine": 20}
        ],
        "agent": {"name": "cyber-agent", "version": "1.0.0", "rubric_hint": "cyber.access_control.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None, "Fail status should produce a SARIF result"
    assert result["level"] == "error", "Fail status should map to error level"
    assert result["ruleId"] == "REQ-001", "ruleId should match requirement uid"
    assert "message" in result
    assert result["message"]["text"] == "Access control mechanisms missing (Score: 0.00, Confidence: 0.80)"


def test_opa_pass_status_produces_no_result() -> None:
    """Test that OPA pass status produces no result (omitted)."""
    requirement = {
        "uid": "REQ-002",
        "key": "CYBER-CRYPTO-001",
        "text": "System must use strong cryptography",
        "subtypes": ["CYBER"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/cyber", "package": "cyber.crypto.v3", "rule": "decision"}],
    }

    decision = {
        "status": "pass",
        "score": 1.0,
        "confidence": 0.95,
        "criteria": [
            {"id": "CRYPTO-1", "status": "pass", "weight": 3, "message": "Strong crypto algorithm detected", "evidence": [0]},
        ],
        "reasons": ["All cryptography requirements met"],
        "policy": {"bundle": "org/cyber", "revision": "2026.01.15", "hash": "def456"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"uses_crypto_library": True, "crypto_algorithms": ["AES-256"]},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/crypto.py", "startLine": 5, "endLine": 10}
        ],
        "agent": {"name": "crypto-agent", "version": "1.0.0", "rubric_hint": "cyber.crypto.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is None, "Pass status should omit result (return None)"


def test_opa_conditional_pass_produces_sarif_warning_result() -> None:
    """Test that OPA conditional_pass status produces SARIF warning result."""
    requirement = {
        "uid": "REQ-003",
        "key": "DATA-PRIVACY-001",
        "text": "System must encrypt sensitive data",
        "subtypes": ["DATA_PRIVACY"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/privacy", "package": "privacy.encryption.v3", "rule": "decision"}],
    }

    decision = {
        "status": "conditional_pass",
        "score": 0.7,
        "confidence": 0.8,
        "criteria": [
            {"id": "ENC-1", "status": "pass", "weight": 2, "message": "Some fields encrypted", "evidence": [0]},
            {"id": "ENC-2", "status": "fail", "weight": 1, "message": "Some fields not encrypted", "evidence": []},
        ],
        "reasons": ["Partial encryption detected; review required"],
        "policy": {"bundle": "org/privacy", "revision": "2026.01.15", "hash": "ghi789"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"pii_fields_encrypted": ["email", "ssn"], "unencrypted_pii": ["phone"]},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/models.py", "startLine": 15, "endLine": 25}
        ],
        "agent": {"name": "privacy-agent", "version": "1.0.0", "rubric_hint": "privacy.encryption.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None, "Conditional_pass status should produce a SARIF result"
    assert result["level"] == "warning", "Conditional_pass status should map to warning level"
    assert result["ruleId"] == "REQ-003", "ruleId should match requirement uid"


def test_rule_id_matches_requirement_uid_stable() -> None:
    """Test that rule.id matches requirement uid and is stable."""
    requirement = {
        "uid": "REQ-STABLE-UID-12345",
        "key": "AUDIT-LOG-001",
        "text": "System must maintain audit logs",
        "subtypes": ["AUDIT"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/audit", "package": "audit.logging.v3", "rule": "decision"}],
    }

    # Create SARIF rule
    rule = create_sarif_rule(requirement)

    # Assertions
    assert rule["id"] == "REQ-STABLE-UID-12345", "rule.id MUST match requirement.uid for stability"
    assert rule["id"] == requirement["uid"], "rule.id and requirement.uid must be identical"
    assert rule["name"] == "AUDIT-LOG-001", "rule.name should be requirement.key"
    assert rule["fullDescription"]["text"] == "System must maintain audit logs"


def test_result_locations_present_when_evidence_has_code_spans() -> None:
    """Test that result.locations are present when evidence includes code spans."""
    requirement = {
        "uid": "REQ-004",
        "key": "CYBER-INPUT-001",
        "text": "System must validate all user inputs",
        "subtypes": ["CYBER"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/cyber", "package": "cyber.input_validation.v3", "rule": "decision"}],
    }

    decision = {
        "status": "fail",
        "score": 0.3,
        "confidence": 0.9,
        "criteria": [
            {"id": "INPUT-1", "status": "fail", "weight": 3, "message": "Missing input validation", "evidence": [0, 1]},
        ],
        "reasons": ["Input validation not implemented in multiple locations"],
        "policy": {"bundle": "org/cyber", "revision": "2026.01.15", "hash": "def456"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"inputs_validated": []},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/api/handlers.py", "startLine": 30, "endLine": 40},
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/api/routes.py", "startLine": 50, "endLine": 60},
            {"type": "artifact", "uri": "artifact://sbom.cdx.json", "hash": "sha256:abc123"},
        ],
        "agent": {"name": "cyber-agent", "version": "1.0.0", "rubric_hint": "cyber.input_validation.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None
    assert "locations" in result, "Result should include locations when evidence has code spans"
    assert len(result["locations"]) == 2, "Should have 2 locations (code_span only, not artifact)"

    # Verify first location
    loc1 = result["locations"][0]
    assert "physicalLocation" in loc1
    assert loc1["physicalLocation"]["artifactLocation"]["uri"] == "api/handlers.py"
    assert loc1["physicalLocation"]["artifactLocation"]["uriBaseId"] == "SRCROOT"
    assert loc1["physicalLocation"]["region"]["startLine"] == 30
    assert loc1["physicalLocation"]["region"]["endLine"] == 40

    # Verify second location
    loc2 = result["locations"][1]
    assert loc2["physicalLocation"]["artifactLocation"]["uri"] == "api/routes.py"
    assert loc2["physicalLocation"]["region"]["startLine"] == 50
    assert loc2["physicalLocation"]["region"]["endLine"] == 60


def test_property_bag_includes_all_required_fields() -> None:
    """Test that result property bag includes all required fields."""
    requirement = {
        "uid": "REQ-005",
        "key": "CYBER-TLS-001",
        "text": "System must use TLS 1.3 or higher",
        "subtypes": ["CYBER", "NETWORK"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/cyber", "package": "cyber.network.v3", "rule": "decision"}],
    }

    decision = {
        "status": "fail",
        "score": 0.0,
        "confidence": 1.0,
        "criteria": [
            {"id": "TLS-1", "status": "fail", "weight": 3, "message": "TLS 1.2 detected", "evidence": [0]},
        ],
        "reasons": ["Outdated TLS version in use"],
        "policy": {"bundle": "org/cyber", "revision": "2026.01.15", "hash": "policy-hash-xyz"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "commit-abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"tls_version": "1.2"},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/server.py", "startLine": 100, "endLine": 105}
        ],
        "agent": {"name": "network-agent", "version": "2.3.0", "rubric_hint": "cyber.network.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None
    assert "properties" in result, "Result must include properties object"

    props = result["properties"]

    # Check all required fields
    assert "requirement_uid" in props, "Property bag must include requirement_uid"
    assert props["requirement_uid"] == "REQ-005"

    assert "requirement_key" in props, "Property bag must include requirement_key"
    assert props["requirement_key"] == "CYBER-TLS-001"

    assert "subtypes" in props, "Property bag must include subtypes"
    assert props["subtypes"] == ["CYBER", "NETWORK"]

    assert "policy_baseline_version" in props, "Property bag must include policy_baseline_version"
    assert props["policy_baseline_version"] == "2026.01"

    assert "opa_policy_hash" in props, "Property bag must include opa_policy_hash"
    assert props["opa_policy_hash"] == "policy-hash-xyz"

    assert "agent_version" in props, "Property bag must include agent_version"
    assert props["agent_version"] == "2.3.0"

    assert "evaluation_id" in props, "Property bag must include evaluation_id"
    assert props["evaluation_id"] == "01JQXYZ123456789ABCDEFGHJK"

    assert "timestamp" in props, "Property bag must include timestamp"

    # Check optional fields
    assert "opa_score" in props
    assert props["opa_score"] == 0.0

    assert "opa_confidence" in props
    assert props["opa_confidence"] == 1.0

    assert "target_repo" in props
    assert props["target_repo"] == "github.com/org/repo"

    assert "target_commit" in props
    assert props["target_commit"] == "commit-abc123"


def test_inconclusive_status_produces_warning_with_triage_needed() -> None:
    """Test that inconclusive status produces warning with triage=needed property."""
    requirement = {
        "uid": "REQ-006",
        "key": "CYBER-AUTH-001",
        "text": "System must implement multi-factor authentication",
        "subtypes": ["CYBER", "ACCESS_CONTROL"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/cyber", "package": "cyber.auth.v3", "rule": "decision"}],
    }

    decision = {
        "status": "inconclusive",
        "score": 0.5,
        "confidence": 0.3,
        "criteria": [
            {"id": "AUTH-1", "status": "na", "weight": 3, "message": "Cannot determine auth mechanism", "evidence": []},
        ],
        "reasons": ["Insufficient evidence to determine MFA implementation"],
        "policy": {"bundle": "org/cyber", "revision": "2026.01.15", "hash": "def456"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"auth_mechanism_detected": False},
        "evidence": [],
        "agent": {"name": "auth-agent", "version": "1.0.0", "rubric_hint": "cyber.auth.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None, "Inconclusive status should produce a SARIF result"
    assert result["level"] == "warning", "Inconclusive status should map to warning level"
    assert "properties" in result
    assert "triage" in result["properties"], "Inconclusive status must include triage property"
    assert result["properties"]["triage"] == "needed", "triage property should be 'needed'"


def test_blocked_status_produces_warning_with_triage_needed() -> None:
    """Test that blocked status produces warning with triage=needed property."""
    requirement = {
        "uid": "REQ-007",
        "key": "AUDIT-RETENTION-001",
        "text": "System must retain audit logs for 90 days",
        "subtypes": ["AUDIT"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/audit", "package": "audit.retention.v3", "rule": "decision"}],
    }

    decision = {
        "status": "blocked",
        "score": 0.0,
        "confidence": 0.0,
        "criteria": [
            {"id": "RET-1", "status": "na", "weight": 3, "message": "Cannot access log configuration", "evidence": []},
        ],
        "reasons": ["Evaluation blocked: log configuration inaccessible"],
        "policy": {"bundle": "org/audit", "revision": "2026.01.15", "hash": "ghi789"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"log_config_accessible": False},
        "evidence": [],
        "agent": {"name": "audit-agent", "version": "1.0.0", "rubric_hint": "audit.retention.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is not None, "Blocked status should produce a SARIF result"
    assert result["level"] == "warning", "Blocked status should map to warning level"
    assert "properties" in result
    assert "triage" in result["properties"], "Blocked status must include triage property"
    assert result["properties"]["triage"] == "needed", "triage property should be 'needed'"


def test_not_applicable_status_produces_no_result() -> None:
    """Test that not_applicable status produces no result (omitted)."""
    requirement = {
        "uid": "REQ-008",
        "key": "MOBILE-SPECIFIC-001",
        "text": "Mobile app must implement biometric authentication",
        "subtypes": ["MOBILE"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/mobile", "package": "mobile.auth.v3", "rule": "decision"}],
    }

    decision = {
        "status": "not_applicable",
        "score": 0.0,
        "confidence": 1.0,
        "criteria": [
            {"id": "MOBILE-1", "status": "na", "weight": 3, "message": "Not a mobile application", "evidence": []},
        ],
        "reasons": ["Requirement not applicable to web application"],
        "policy": {"bundle": "org/mobile", "revision": "2026.01.15", "hash": "jkl012"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"application_type": "web"},
        "evidence": [],
        "agent": {"name": "mobile-agent", "version": "1.0.0", "rubric_hint": "mobile.auth.v3"},
    }

    evaluation_id = "01JQXYZ123456789ABCDEFGHJK"

    # Create SARIF result
    result = create_sarif_result(requirement, decision, facts, evaluation_id)

    # Assertions
    assert result is None, "Not_applicable status should omit result (return None)"


def test_status_to_level_mapping() -> None:
    """Test the OPA status to SARIF level mapping function."""
    # Test all status mappings
    assert _map_status_to_level("pass") is None, "pass should map to None (omit)"
    assert _map_status_to_level("fail") == "error", "fail should map to error"
    assert _map_status_to_level("conditional_pass") == "warning", "conditional_pass should map to warning"
    assert _map_status_to_level("inconclusive") == "warning", "inconclusive should map to warning"
    assert _map_status_to_level("blocked") == "warning", "blocked should map to warning"
    assert _map_status_to_level("not_applicable") is None, "not_applicable should map to None (omit)"
    assert _map_status_to_level("waived") == "note", "waived should map to note"
    assert _map_status_to_level("unknown_status") is None, "unknown status should default to None"


def test_extract_evidence_locations_filters_code_spans() -> None:
    """Test that evidence extraction filters to code_span type only."""
    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"test": True},
        "evidence": [
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/file1.py", "startLine": 10, "endLine": 20},
            {"type": "artifact", "uri": "artifact://sbom.json", "hash": "sha256:abc123"},
            {"type": "log", "uri": "file:///var/log/app.log"},
            {"type": "code_span", "uri": "repo://github.com/org/repo/src/file2.py", "startLine": 30},
            {"type": "metric", "uri": "metric://cpu_usage", "value": 0.8},
        ],
        "agent": {"name": "test-agent", "version": "1.0.0"},
    }

    # Extract evidence locations
    locations = _extract_evidence_locations(facts)

    # Assertions
    assert len(locations) == 2, "Should extract only code_span evidence (2 items)"

    # Verify first location
    assert locations[0]["physicalLocation"]["artifactLocation"]["uri"] == "file1.py"
    assert locations[0]["physicalLocation"]["region"]["startLine"] == 10
    assert locations[0]["physicalLocation"]["region"]["endLine"] == 20

    # Verify second location
    assert locations[1]["physicalLocation"]["artifactLocation"]["uri"] == "file2.py"
    assert locations[1]["physicalLocation"]["region"]["startLine"] == 30
    assert "endLine" not in locations[1]["physicalLocation"]["region"], "endLine should be optional"


def test_generate_sarif_report_complete_structure() -> None:
    """Test that generate_sarif_report produces complete SARIF v2.1.0 structure."""
    requirement = {
        "uid": "REQ-COMPLETE",
        "key": "TEST-001",
        "text": "Complete test requirement",
        "subtypes": ["TEST"],
        "policy_baseline": {"id": "POL-2026.01", "version": "2026.01", "hash": "abc123"},
        "rubrics": [{"engine": "opa", "bundle": "org/test", "package": "test.v3", "rule": "decision"}],
    }

    decision = {
        "status": "fail",
        "score": 0.5,
        "confidence": 0.8,
        "criteria": [
            {"id": "TEST-1", "status": "fail", "weight": 3, "message": "Test failed", "evidence": []},
        ],
        "reasons": ["Test failure detected"],
        "policy": {"bundle": "org/test", "revision": "1.0.0", "hash": "bundle-hash-123"},
    }

    facts = {
        "target": {"repo": "github.com/org/repo", "commit": "abc123", "build": "2026-01-31T10:00:00Z"},
        "facts": {"test": True},
        "evidence": [],
        "agent": {"name": "test-agent", "version": "1.0.0"},
    }

    # Generate SARIF report
    report = generate_sarif_report(requirement, decision, facts)

    # Verify top-level structure
    assert "$schema" in report
    assert report["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert report["version"] == "2.1.0"
    assert "runs" in report
    assert len(report["runs"]) == 1

    # Verify run structure
    run = report["runs"][0]
    assert "tool" in run
    assert "driver" in run["tool"]
    assert run["tool"]["driver"]["name"] == "org/test"
    assert run["tool"]["driver"]["version"] == "1.0.0"
    assert "rules" in run["tool"]["driver"]
    assert len(run["tool"]["driver"]["rules"]) == 1

    # Verify rule
    rule = run["tool"]["driver"]["rules"][0]
    assert rule["id"] == "REQ-COMPLETE"
    assert rule["name"] == "TEST-001"

    # Verify results
    assert "results" in run
    assert len(run["results"]) == 1, "Fail status should produce a result"

    # Verify run properties
    assert "properties" in run
    assert run["properties"]["policy_bundle"] == "org/test"
    assert run["properties"]["policy_revision"] == "1.0.0"
    assert run["properties"]["policy_hash"] == "bundle-hash-123"
