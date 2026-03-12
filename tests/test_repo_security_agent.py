"""Tests for the deterministic repo-security agent."""

from __future__ import annotations

from pathlib import Path

from agents.repo_security_agent import build_repo_security_facts


def test_repo_security_agent_surfaces_expected_controls() -> None:
    """The repo-security agent should expose stable control booleans."""
    facts = build_repo_security_facts(Path.cwd())
    controls = facts["facts"]["controls"]

    assert controls["toolchain_security_tools_defined"] is True
    assert controls["code_analysis_findings_recorded"] is True
    assert controls["repo_vulnerability_scan_task_present"] is True
    assert controls["vulnerability_disclosure_policy_present"] is False


def test_repo_security_agent_tracks_selected_cwes() -> None:
    """The repo-security agent should return findings for the chosen CWE sample set."""
    facts = build_repo_security_facts(Path.cwd())
    cwe_findings = facts["facts"]["cwe_findings"]

    assert cwe_findings["CWE-20"]
    assert cwe_findings["CWE-22"]
    assert cwe_findings["CWE-400"]
    assert cwe_findings["CWE-532"]
    assert cwe_findings["CWE-862"]
    assert cwe_findings["CWE-78"] == []
