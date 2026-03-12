package ssdf.secure_software.v1

import rego.v1

default decision := {
	"status": "inconclusive",
	"score": 0.0,
	"confidence": 0.0,
	"criteria": [],
	"reasons": ["No NIST SSDF evaluation could be derived for this requirement."],
	"policy": {
		"bundle": "org/nist-ssdf-sample",
		"revision": "2026.03.12",
		"hash": "nist-ssdf-sample",
	},
}

decision := result if {
	requirement := input.requirement
	controls := object.get(input.facts.facts, "controls", {})
	control_id := object.get(object.get(requirement, "attrs", {}), "control_id", "")
	criterion := evaluate_control(requirement, control_id, controls)
	result := {
		"status": overall_status(criterion.status),
		"score": score_for_status(criterion.status),
		"confidence": 0.7,
		"criteria": [criterion],
		"reasons": [criterion.message],
		"policy": {
			"bundle": "org/nist-ssdf-sample",
			"revision": "2026.03.12",
			"hash": "nist-ssdf-sample",
		},
	}
}

evaluate_control(requirement, control_id, controls) := criterion if {
	state := control_state(control_id, controls)
	criterion := {
		"id": object.get(requirement, "key", control_id),
		"status": state.status,
		"weight": 1,
		"message": state.message,
		"evidence": [],
	}
}

control_state("PO.3.1", controls) := {"status": "pass", "message": "Security tooling is defined in the repo toolchain."} if object.get(controls, "toolchain_security_tools_defined", false)
control_state("PO.3.1", controls) := {"status": "fail", "message": "The repo does not define a consistent security tooling chain."} if not object.get(controls, "toolchain_security_tools_defined", false)

control_state("PW.7.2", controls) := {"status": "pass", "message": "Code-analysis findings are recorded and surfaced in workflow artifacts."} if object.get(controls, "code_analysis_findings_recorded", false)
control_state("PW.7.2", controls) := {"status": "fail", "message": "The repo does not record and surface code-analysis findings in its workflow."} if not object.get(controls, "code_analysis_findings_recorded", false)

control_state("RV.1.2", controls) := {"status": "pass", "message": "A dedicated repo vulnerability scan task is present for dogfooding."} if object.get(controls, "repo_vulnerability_scan_task_present", false)
control_state("RV.1.2", controls) := {"status": "fail", "message": "The repo lacks a dedicated dogfood vulnerability scan task."} if not object.get(controls, "repo_vulnerability_scan_task_present", false)

control_state("RV.1.3", controls) := {"status": "pass", "message": "A vulnerability disclosure or remediation policy is present."} if object.get(controls, "vulnerability_disclosure_policy_present", false)
control_state("RV.1.3", controls) := {"status": "fail", "message": "No repository vulnerability disclosure or remediation policy was found."} if not object.get(controls, "vulnerability_disclosure_policy_present", false)

control_state(control_id, _) := {"status": "inconclusive", "message": "No SSDF state mapping exists for this control."} if {
	control_id != "PO.3.1"
	control_id != "PW.7.2"
	control_id != "RV.1.2"
	control_id != "RV.1.3"
}

overall_status("pass") := "pass"
overall_status("fail") := "fail"
overall_status(status) := "inconclusive" if {
	status != "pass"
	status != "fail"
}

score_for_status("pass") := 1.0
score_for_status(status) := 0.0 if status != "pass"
