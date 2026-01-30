# OPA policy tests for cyber.access_control.v3 package
# Run with: opa test opa-bundles/example

package cyber.access_control.v3

import rego.v1

# Test 1: Pass - crypto requirement with crypto library usage
test_crypto_requirement_with_crypto_library_passes if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-001",
			"key": "CYBER-AC-001",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use cryptographic libraries for all sensitive data",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "abc123",
				"build": "build-456",
			},
			"facts": {"uses_crypto_library": true},
			"evidence": [
				{
					"type": "code_span",
					"uri": "repo://github.com/org/repo/src/crypto/aes.py",
					"startLine": 10,
					"endLine": 25,
				},
				{
					"type": "code_span",
					"uri": "repo://github.com/org/repo/src/crypto/rsa.py",
					"startLine": 5,
					"endLine": 15,
				},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
				"rubric_hint": "cyber.access_control.v3",
			},
		},
		"context": {},
	}

	# Assert overall status is pass
	result.status == "pass"

	# Assert score is 1.0 (all criteria passed)
	result.score == 1.0

	# Assert confidence is high (2 evidence items)
	result.confidence == 0.6

	# Assert crypto criterion passed
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	crypto_criterion.status == "pass"
	crypto_criterion.weight == 3

	# Assert input validation criterion is N/A (not in requirement text)
	input_criterion := [c | c := result.criteria[_]; c.id == "CYBER-INPUT-1"][0]
	input_criterion.status == "na"
	input_criterion.weight == 0

	# Assert reasons includes crypto success message
	count([r | r := result.reasons[_]; contains(r, "Cryptographic library")]) > 0
}

# Test 2: Fail - crypto requirement without crypto library
test_crypto_requirement_without_crypto_library_fails if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-002",
			"key": "CYBER-AC-002",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use approved cryptographic algorithms",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "def456",
				"build": "build-789",
			},
			"facts": {"uses_crypto_library": false},
			"evidence": [],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert overall status is fail
	result.status == "fail"

	# Assert score is 0.0 (crypto criterion failed)
	result.score == 0.0

	# Assert confidence is low (no evidence)
	result.confidence == 0.3

	# Assert crypto criterion failed
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	crypto_criterion.status == "fail"
	crypto_criterion.message == "No cryptographic library usage found - requirement may not be satisfied"
}

# Test 3: Pass - input validation requirement with all inputs validated
test_input_validation_requirement_passes if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-003",
			"key": "CYBER-AC-003",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall validate all user inputs before processing",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "ghi789",
				"build": "build-123",
			},
			"facts": {"inputs_validated": []},
			"evidence": [
				{
					"type": "code_span",
					"uri": "repo://github.com/org/repo/src/input/validator.py",
					"startLine": 20,
					"endLine": 40,
				},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert overall status is pass
	result.status == "pass"

	# Assert score is 1.0 (input validation passed)
	result.score == 1.0

	# Assert input validation criterion passed
	input_criterion := [c | c := result.criteria[_]; c.id == "CYBER-INPUT-1"][0]
	input_criterion.status == "pass"
	input_criterion.weight == 4
	input_criterion.message == "All inputs properly validated"
}

# Test 4: Fail - input validation requirement with validation issues
test_input_validation_requirement_with_issues_fails if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-004",
			"key": "CYBER-AC-004",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall validate all inputs for SQL injection",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "jkl012",
				"build": "build-456",
			},
			"facts": {
				"inputs_validated": [
					{"path": "src/api/users.py", "line": 44, "kind": "missing"},
					{"path": "src/api/orders.py", "line": 88, "kind": "missing"},
				],
			},
			"evidence": [
				{
					"type": "code_span",
					"uri": "repo://github.com/org/repo/src/api/users.py",
					"startLine": 44,
					"endLine": 50,
				},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert overall status is fail
	result.status == "fail"

	# Assert score is 0.0 (input validation failed)
	result.score == 0.0

	# Assert input validation criterion failed
	input_criterion := [c | c := result.criteria[_]; c.id == "CYBER-INPUT-1"][0]
	input_criterion.status == "fail"
	input_criterion.message == "Found 2 input validation issues"
}

# Test 5: Not applicable - requirement doesn't match crypto or input validation
test_non_matching_requirement_returns_not_applicable if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-005",
			"key": "CYBER-AC-005",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall implement rate limiting on API endpoints",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "mno345",
				"build": "build-789",
			},
			"facts": {},
			"evidence": [],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert overall status is not_applicable
	result.status == "not_applicable"

	# Assert both criteria are N/A
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	crypto_criterion.status == "na"

	input_criterion := [c | c := result.criteria[_]; c.id == "CYBER-INPUT-1"][0]
	input_criterion.status == "na"
}

# Test 6: Edge case - missing facts object
test_missing_facts_object if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-006",
			"key": "CYBER-AC-006",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use crypto libraries",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "pqr678",
				"build": "build-012",
			},
			"facts": {},
			"evidence": [],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert crypto criterion fails (uses_crypto_library defaults to false)
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	crypto_criterion.status == "fail"

	# Assert overall status is fail
	result.status == "fail"
}

# Test 7: Edge case - empty evidence array
test_empty_evidence_array if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-007",
			"key": "CYBER-AC-007",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use cryptographic algorithms",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "stu901",
				"build": "build-345",
			},
			"facts": {"uses_crypto_library": true},
			"evidence": [],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert confidence is low (no evidence)
	result.confidence == 0.3

	# Assert status still passes (based on facts, not evidence)
	result.status == "pass"

	# Assert crypto criterion has empty evidence array
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	count(crypto_criterion.evidence) == 0
}

# Test 8: Boundary condition - exactly 3 evidence items (confidence boundary)
test_confidence_with_three_evidence_items if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-008",
			"key": "CYBER-AC-008",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use crypto",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "vwx234",
				"build": "build-678",
			},
			"facts": {"uses_crypto_library": true},
			"evidence": [
				{"type": "code_span", "uri": "repo://a.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://b.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://c.py", "startLine": 1, "endLine": 10},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert confidence is 0.8 (3 evidence items)
	result.confidence == 0.8
}

# Test 9: Boundary condition - exactly 5 evidence items (max confidence)
test_confidence_with_five_evidence_items if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-009",
			"key": "CYBER-AC-009",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use crypto",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "yzab567",
				"build": "build-901",
			},
			"facts": {"uses_crypto_library": true},
			"evidence": [
				{"type": "code_span", "uri": "repo://a.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://b.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://c.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://d.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://e.py", "startLine": 1, "endLine": 10},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert confidence is 1.0 (5+ evidence items)
	result.confidence == 1.0
}

# Test 10: Mixed criteria - one pass, one fail
test_mixed_criteria_crypto_and_input_validation if {
	result := decision with input as {
		"requirement": {
			"uid": "REQ-010",
			"key": "CYBER-AC-010",
			"subtypes": ["CYBER"],
			"status": "active",
			"text": "System shall use crypto libraries and validate all inputs",
			"policy_baseline": {
				"id": "POL-2026.01",
				"version": "2026.01",
				"hash": "abc123",
			},
			"rubrics": [{
				"engine": "opa",
				"bundle": "org/cyber",
				"package": "cyber.access_control.v3",
				"rule": "decision",
			}],
		},
		"facts": {
			"target": {
				"repo": "github.com/org/repo",
				"commit": "cdef890",
				"build": "build-234",
			},
			"facts": {
				"uses_crypto_library": true,
				"inputs_validated": [{"path": "src/api.py", "line": 10, "kind": "missing"}],
			},
			"evidence": [
				{"type": "code_span", "uri": "repo://crypto.py", "startLine": 1, "endLine": 10},
				{"type": "code_span", "uri": "repo://input.py", "startLine": 1, "endLine": 10},
			],
			"agent": {
				"name": "cyber-agent",
				"version": "1.0.0",
			},
		},
		"context": {},
	}

	# Assert overall status is fail (any criterion failed)
	result.status == "fail"

	# Assert score is weighted average: crypto passed (3), input failed (4), so 3/7
	result.score == 3.0 / 7.0

	# Assert crypto criterion passed
	crypto_criterion := [c | c := result.criteria[_]; c.id == "CYBER-CRYPTO-1"][0]
	crypto_criterion.status == "pass"

	# Assert input criterion failed
	input_criterion := [c | c := result.criteria[_]; c.id == "CYBER-INPUT-1"][0]
	input_criterion.status == "fail"

	# Assert reasons includes both messages
	count(result.reasons) == 2
}
