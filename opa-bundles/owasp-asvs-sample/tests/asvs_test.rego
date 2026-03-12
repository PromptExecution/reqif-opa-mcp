package asvs.python_secure_coding.v1

import rego.v1

test_input_validation_requirement_passes if {
	result := decision with input as {
		"requirement": {
			"key": "V2-2-1",
			"attrs": {"cwe": "CWE-20"},
		},
		"facts": {
			"facts": {
				"cwe_findings": {"CWE-20": []},
				"controls": {"remote_fetch_capability_present": false, "remote_fetch_allowlist_present": false},
			},
			"evidence": [],
		},
	}
	result.status == "pass"
}

test_command_injection_requirement_fails if {
	result := decision with input as {
		"requirement": {
			"key": "V1-2-5",
			"attrs": {"cwe": "CWE-78"},
		},
		"facts": {
			"facts": {
				"cwe_findings": {"CWE-78": [{"message": "shell execution found"}]},
				"controls": {"remote_fetch_capability_present": false, "remote_fetch_allowlist_present": false},
			},
			"evidence": [],
		},
	}
	result.status == "fail"
}

test_ssrf_requirement_is_not_applicable_without_remote_fetch if {
	result := decision with input as {
		"requirement": {
			"key": "V1-3-6",
			"attrs": {"cwe": "CWE-918"},
		},
		"facts": {
			"facts": {
				"cwe_findings": {"CWE-918": []},
				"controls": {"remote_fetch_capability_present": false, "remote_fetch_allowlist_present": false},
			},
			"evidence": [],
		},
	}
	result.status == "not_applicable"
}
