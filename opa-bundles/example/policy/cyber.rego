# Example OPA policy for CYBER subtype requirements
# This demonstrates the structure expected by the reqif-opa-sarif compliance gate system

package cyber.access_control.v3

import rego.v1

# Default decision when no rules match
default decision := {
	"status": "inconclusive",
	"score": 0.0,
	"confidence": 0.0,
	"criteria": [],
	"reasons": ["No matching evaluation rules for this requirement"],
	"policy": {
		"bundle": "org/cyber",
		"revision": "v3.0.0",
		"hash": "example-hash-placeholder",
	},
}

# Main decision rule - evaluates requirement against facts
decision := result if {
	# Access input fields (requirement, facts, context)
	requirement := input.requirement
	facts := input.facts

	# Evaluate individual criteria
	crypto_criterion := evaluate_crypto_usage(requirement, facts)
	input_validation_criterion := evaluate_input_validation(requirement, facts)

	# Aggregate criteria
	criteria := [crypto_criterion, input_validation_criterion]

	# Calculate overall score (weighted average of passing criteria)
	score := calculate_score(criteria)

	# Determine overall status
	status := determine_status(criteria)

	# Calculate confidence based on evidence availability
	confidence := calculate_confidence(facts)

	# Generate reasons
	reasons := generate_reasons(criteria)

	# Build result
	result := {
		"status": status,
		"score": score,
		"confidence": confidence,
		"criteria": criteria,
		"reasons": reasons,
		"policy": {
			"bundle": "org/cyber",
			"revision": "v3.0.0",
			"hash": "example-hash-placeholder",
		},
	}
}

# Criterion: Evaluate cryptographic library usage
evaluate_crypto_usage(requirement, facts) := criterion if {
	# Check if requirement mentions cryptography
	contains(lower(requirement.text), "crypto")

	# Check facts for crypto library usage
	uses_crypto := object.get(facts.facts, "uses_crypto_library", false)

	# Find relevant evidence indices
	evidence_indices := [i |
		facts.evidence[i].type == "code_span"
		contains(facts.evidence[i].uri, "crypto")
	]

	# Build criterion result
	criterion := {
		"id": "CYBER-CRYPTO-1",
		"status": crypto_status(uses_crypto),
		"weight": 3,
		"message": crypto_message(uses_crypto),
		"evidence": evidence_indices,
	}
}

# Fallback for non-crypto requirements
evaluate_crypto_usage(requirement, facts) := criterion if {
	not contains(lower(requirement.text), "crypto")

	criterion := {
		"id": "CYBER-CRYPTO-1",
		"status": "na",
		"weight": 0,
		"message": "Cryptography not applicable to this requirement",
		"evidence": [],
	}
}

crypto_status(uses_crypto) := "pass" if uses_crypto
crypto_status(uses_crypto) := "fail" if not uses_crypto

crypto_message(true) := "Cryptographic library usage detected"
crypto_message(false) := "No cryptographic library usage found - requirement may not be satisfied"

# Criterion: Evaluate input validation
evaluate_input_validation(requirement, facts) := criterion if {
	# Check if requirement mentions input validation
	contains(lower(requirement.text), "input")
	contains(lower(requirement.text), "valid")

	# Check facts for input validation issues
	inputs_validated := object.get(facts.facts, "inputs_validated", [])
	has_issues := count(inputs_validated) > 0

	# Find relevant evidence indices
	evidence_indices := [i |
		facts.evidence[i].type == "code_span"
		contains(facts.evidence[i].uri, "input")
	]

	# Build criterion result
	criterion := {
		"id": "CYBER-INPUT-1",
		"status": input_status(has_issues),
		"weight": 4,
		"message": input_message(has_issues, count(inputs_validated)),
		"evidence": evidence_indices,
	}
}

# Fallback for non-input-validation requirements
evaluate_input_validation(requirement, facts) := criterion if {
	not contains(lower(requirement.text), "input")

	criterion := {
		"id": "CYBER-INPUT-1",
		"status": "na",
		"weight": 0,
		"message": "Input validation not applicable to this requirement",
		"evidence": [],
	}
}

input_status(has_issues) := "fail" if has_issues
input_status(has_issues) := "pass" if not has_issues

input_message(false, _) := "All inputs properly validated"
input_message(true, count) := sprintf("Found %d input validation issues", [count])

# Calculate overall score (weighted average of passing criteria)
calculate_score(criteria) := 0.0 if {
	# When all criteria are N/A (total_weight = 0), return 0.0
	total_weight := sum([c.weight | c := criteria[_]])
	total_weight == 0
}

calculate_score(criteria) := score if {
	# Normal case: calculate weighted average
	total_weight := sum([c.weight | c := criteria[_]])
	passed_weight := sum([c.weight | c := criteria[_]; c.status == "pass"])
	total_weight > 0
	score := passed_weight / total_weight
}

# Determine overall status from criteria
determine_status(criteria) := "pass" if {
	# All criteria either pass or not applicable
	count([c | c := criteria[_]; c.status == "fail"]) == 0
	count([c | c := criteria[_]; c.status == "pass"]) > 0
}

determine_status(criteria) := "fail" if {
	# Any criterion failed
	count([c | c := criteria[_]; c.status == "fail"]) > 0
}

determine_status(criteria) := "not_applicable" if {
	# All criteria are not applicable
	count([c | c := criteria[_]; c.status != "na"]) == 0
}

determine_status(criteria) := "inconclusive" if {
	# No criteria passed or failed (edge case)
	count([c | c := criteria[_]; c.status == "pass"]) == 0
	count([c | c := criteria[_]; c.status == "fail"]) == 0
	count([c | c := criteria[_]; c.status != "na"]) > 0
}

# Calculate confidence based on evidence availability
# Simple heuristic: more evidence = higher confidence
# 0 evidence = 0.3 confidence, 1-2 = 0.6, 3-4 = 0.8, 5+ = 1.0
calculate_confidence(facts) := 0.3 if {
	count(facts.evidence) == 0
}

calculate_confidence(facts) := 0.6 if {
	evidence_count := count(facts.evidence)
	evidence_count >= 1
	evidence_count < 3
}

calculate_confidence(facts) := 0.8 if {
	evidence_count := count(facts.evidence)
	evidence_count >= 3
	evidence_count < 5
}

calculate_confidence(facts) := 1.0 if {
	count(facts.evidence) >= 5
}

# Default confidence if none of the above match
default calculate_confidence(_) := 0.5

# Generate human-readable reasons from criteria
generate_reasons(criteria) := reasons if {
	failed := [c.message | c := criteria[_]; c.status == "fail"]
	passed := [c.message | c := criteria[_]; c.status == "pass"]

	reasons := array.concat(failed, passed)
}

