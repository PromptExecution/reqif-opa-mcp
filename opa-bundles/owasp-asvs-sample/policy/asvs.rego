package asvs.python_secure_coding.v1

import rego.v1

default decision := {
	"status": "inconclusive",
	"score": 0.0,
	"confidence": 0.0,
	"criteria": [],
	"reasons": ["No OWASP ASVS evaluation could be derived for this requirement."],
	"policy": {
		"bundle": "org/owasp-asvs-sample",
		"revision": "2026.03.12",
		"hash": "owasp-asvs-sample",
	},
}

decision := result if {
	requirement := input.requirement
	facts := input.facts
	attrs := object.get(requirement, "attrs", {})
	controls := object.get(facts.facts, "controls", {})
	cwe := object.get(attrs, "cwe", "")
	findings := object.get(object.get(facts.facts, "cwe_findings", {}), cwe, [])
	criterion := evaluate_control(requirement, cwe, findings, controls)
	result := {
		"status": overall_status(criterion.status),
		"score": score_for_status(criterion.status),
		"confidence": confidence_for_findings(findings),
		"criteria": [criterion],
		"reasons": [criterion.message],
		"policy": {
			"bundle": "org/owasp-asvs-sample",
			"revision": "2026.03.12",
			"hash": "owasp-asvs-sample",
		},
	}
}

evaluate_control(requirement, cwe, findings, controls) := criterion if {
	cwe == "CWE-918"
	not object.get(controls, "remote_fetch_capability_present", false)
	criterion := {
		"id": object.get(requirement, "key", cwe),
		"status": "na",
		"weight": 1,
		"message": "Remote fetching is not enabled in the repo-scanned application surface.",
		"evidence": [],
	}
}

evaluate_control(requirement, cwe, findings, controls) := criterion if {
	cwe == "CWE-918"
	object.get(controls, "remote_fetch_capability_present", false)
	not object.get(controls, "remote_fetch_allowlist_present", false)
	criterion := {
		"id": object.get(requirement, "key", cwe),
		"status": "fail",
		"weight": 1,
		"message": "Remote fetching is present without an explicit allowlist control.",
		"evidence": [],
	}
}

evaluate_control(requirement, cwe, findings, _) := criterion if {
	cwe != "CWE-918"
	count(findings) > 0
	criterion := {
		"id": object.get(requirement, "key", cwe),
		"status": "fail",
		"weight": 1,
		"message": findings[0].message,
		"evidence": [],
	}
}

evaluate_control(requirement, cwe, findings, controls) := criterion if {
	cwe == "CWE-918"
	object.get(controls, "remote_fetch_capability_present", false)
	object.get(controls, "remote_fetch_allowlist_present", false)
	criterion := {
		"id": object.get(requirement, "key", cwe),
		"status": "pass",
		"weight": 1,
		"message": sprintf("No repo finding was recorded for %v.", [cwe]),
		"evidence": [],
	}
}

evaluate_control(requirement, cwe, findings, _) := criterion if {
	cwe != "CWE-918"
	count(findings) == 0
	criterion := {
		"id": object.get(requirement, "key", cwe),
		"status": "pass",
		"weight": 1,
		"message": sprintf("No repo finding was recorded for %v.", [cwe]),
		"evidence": [],
	}
}

overall_status("pass") := "pass"
overall_status("fail") := "fail"
overall_status("na") := "not_applicable"
overall_status(status) := "inconclusive" if {
	status != "pass"
	status != "fail"
	status != "na"
}

score_for_status("pass") := 1.0
score_for_status(status) := 0.0 if status != "pass"

confidence_for_findings(findings) := 0.8 if count(findings) > 0
confidence_for_findings(findings) := 0.6 if count(findings) == 0
