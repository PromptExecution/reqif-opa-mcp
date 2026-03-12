"""Tests for compliance gate meta-policy and error handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from returns.result import Failure, Success

from reqif_mcp.compliance_gate import run_compliance_gate

OPA_BUNDLE = Path("opa-bundles/example")
SAMPLE_REQIF = Path("tests/fixtures/sample_baseline.reqif")


def test_compliance_gate_fails_on_empty_baseline(tmp_path: Path) -> None:
    """A ReqIF baseline with zero requirements is a hard meta-policy failure."""
    reqif_path = tmp_path / "empty.reqif"
    reqif_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Empty Baseline</TITLE>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES />
    <SPEC-OBJECTS />
  </REQ-IF-CONTENT>
</REQ-IF>
""",
        encoding="utf-8",
    )
    facts_path = _write_facts(tmp_path, subtype="CYBER")

    exit_code = run_compliance_gate(
        reqif_path=reqif_path,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="CYBER",
        package="cyber.access_control.v3",
        baseline_id="TEST-EMPTY",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 2
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] == "failed_meta_policy"
    assert _issue_codes(summary["meta_policy_failures"]) >= {"EMPTY_BASELINE", "EMPTY_SELECTION"}


def test_compliance_gate_fails_on_empty_selection(tmp_path: Path) -> None:
    """Selecting zero requirements must fail explicitly."""
    facts_path = _write_facts(tmp_path, subtype="CYBER")

    exit_code = run_compliance_gate(
        reqif_path=SAMPLE_REQIF,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="NOT_A_REAL_SUBTYPE",
        package="cyber.access_control.v3",
        baseline_id="TEST-SELECTION",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 2
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["selected_requirement_count"] == 0
    assert "EMPTY_SELECTION" in _issue_codes(summary["meta_policy_failures"])


def test_compliance_gate_surfaces_processing_failures(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Evaluation errors must be collected and surfaced, not silently skipped."""
    facts_path = _write_facts(tmp_path, subtype="CYBER")

    def failing_evaluation(*args: Any, **kwargs: Any) -> Any:
        return Failure(RuntimeError("opa blew up"))

    monkeypatch.setattr("reqif_mcp.compliance_gate.evaluate_requirement", failing_evaluation)

    exit_code = run_compliance_gate(
        reqif_path=SAMPLE_REQIF,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="CYBER",
        package="cyber.access_control.v3",
        baseline_id="TEST-PROCESSING",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 3
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] == "failed_processing"
    assert summary["successful_evaluations"] == 0
    assert _issue_codes(summary["processing_failures"]) >= {
        "OPA_EVALUATION_FAILED",
        "ZERO_SUCCESSFUL_EVALUATIONS",
    }


def test_compliance_gate_reports_gate_failures(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """High-severity policy failures must produce a failed gate summary."""
    facts_path = _write_facts(tmp_path, subtype="CYBER")

    def failing_decision(*args: Any, **kwargs: Any) -> Any:
        return Success(
            {
                "status": "fail",
                "score": 0.0,
                "confidence": 0.8,
                "criteria": [],
                "reasons": ["policy failure"],
                "policy": {
                    "bundle": "org/cyber",
                    "revision": "v3.0.0",
                    "hash": "hash",
                },
            }
        )

    monkeypatch.setattr("reqif_mcp.compliance_gate.evaluate_requirement", failing_decision)
    monkeypatch.setattr(
        "reqif_mcp.compliance_gate.reqif_write_verification",
        lambda event: {"success": True, "event_id": "evt-1"},
    )

    exit_code = run_compliance_gate(
        reqif_path=SAMPLE_REQIF,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="CYBER",
        package="cyber.access_control.v3",
        baseline_id="TEST-GATE",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 4
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] == "failed_gate"
    assert summary["successful_evaluations"] == 2
    assert summary["result_counts"]["fail"] == 2
    assert "HIGH_SEVERITY_POLICY_FAILURE" in _issue_codes(summary["gate_failures"])


def test_compliance_gate_fails_on_incomplete_facts(tmp_path: Path) -> None:
    """Incomplete facts payloads must fail before evaluation starts."""
    facts_path = tmp_path / "agent_facts.json"
    facts_path.write_text(
        json.dumps(
            {
                "target": {
                    "repo": "PromptExecution/reqif-opa-mcp",
                },
                "facts": {"subtype": "CYBER"},
                "evidence": [],
                "agent": {"name": "test-agent"},
            }
        ),
        encoding="utf-8",
    )

    exit_code = run_compliance_gate(
        reqif_path=SAMPLE_REQIF,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="CYBER",
        package="cyber.access_control.v3",
        baseline_id="TEST-INCOMPLETE-FACTS",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 2
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] == "failed_meta_policy"
    assert _issue_codes(summary["meta_policy_failures"]) >= {
        "EMPTY_EVIDENCE",
        "TARGET_METADATA_INCOMPLETE",
        "AGENT_METADATA_INCOMPLETE",
    }


def test_compliance_gate_fails_on_bundle_package_mismatch(tmp_path: Path) -> None:
    """A package override that does not align to the bundle root must fail explicitly."""
    facts_path = _write_facts(tmp_path, subtype="CYBER")

    exit_code = run_compliance_gate(
        reqif_path=SAMPLE_REQIF,
        facts_path=facts_path,
        bundle_path=OPA_BUNDLE,
        subtype="CYBER",
        package="finance.access_control.v1",
        baseline_id="TEST-PACKAGE-MISMATCH",
        baseline_version="1.0.0",
        out_dir=tmp_path,
    )

    assert exit_code == 2
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert "PACKAGE_ROOT_MISMATCH" in _issue_codes(summary["meta_policy_failures"])


def _write_facts(tmp_path: Path, subtype: str) -> Path:
    """Write a minimal valid facts payload."""
    facts_path = tmp_path / "agent_facts.json"
    payload = {
        "target": {
            "repo": "PromptExecution/reqif-opa-mcp",
            "commit": "abc123",
            "build": "test-build",
        },
        "facts": {
            "subtype": subtype,
        },
        "evidence": [
            {
                "type": "code_span",
                "uri": "repo://PromptExecution/reqif-opa-mcp/README.md",
                "startLine": 1,
                "endLine": 2,
            }
        ],
        "agent": {
            "name": "test-agent",
            "version": "0.1.0",
            "rubric_hint": "cyber.access_control.v3",
        },
    }
    facts_path.write_text(json.dumps(payload), encoding="utf-8")
    return facts_path


def _issue_codes(issues: list[dict[str, Any]]) -> set[str]:
    """Collect issue codes from summary JSON."""
    return {str(issue["code"]) for issue in issues}
