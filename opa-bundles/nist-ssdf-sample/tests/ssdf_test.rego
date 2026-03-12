package ssdf.secure_software.v1

import rego.v1

test_toolchain_control_passes if {
	result := decision with input as {
		"requirement": {
			"key": "PO-3-1",
			"attrs": {"control_id": "PO.3.1"},
		},
		"facts": {
			"facts": {
				"controls": {
					"toolchain_security_tools_defined": true,
					"code_analysis_findings_recorded": true,
					"repo_vulnerability_scan_task_present": true,
					"vulnerability_disclosure_policy_present": false,
				},
			},
		},
	}
	result.status == "pass"
}

test_disclosure_policy_control_fails_without_policy if {
	result := decision with input as {
		"requirement": {
			"key": "RV-1-3",
			"attrs": {"control_id": "RV.1.3"},
		},
		"facts": {
			"facts": {
				"controls": {
					"toolchain_security_tools_defined": true,
					"code_analysis_findings_recorded": true,
					"repo_vulnerability_scan_task_present": true,
					"vulnerability_disclosure_policy_present": false,
				},
			},
		},
	}
	result.status == "fail"
}
