#!/usr/bin/env python3
"""Deterministic repo-security agent for local dogfooding.

This agent scans the current repository for a small, explicit set of
security-significant patterns so sample policy bundles can evaluate the repo
against OWASP ASVS and NIST SSDF controls without needing an LLM.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Finding:
    """A deterministic security finding with a source location."""

    cwe: str
    message: str
    path: str
    line: int
    severity: str = "high"

    def as_fact(self) -> dict[str, Any]:
        """Render a finding for the facts payload."""
        return {
            "cwe": self.cwe,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
        }

    def as_evidence(self) -> dict[str, Any]:
        """Render a finding as evidence."""
        return {
            "type": "code_span",
            "uri": f"repo://{self.path}",
            "startLine": self.line,
            "endLine": self.line,
        }


def build_repo_security_facts(root: Path) -> dict[str, Any]:
    """Build the facts/1 payload for the repository."""
    findings = _collect_findings(root)
    controls = _collect_controls(root)
    evidence = [
        finding.as_evidence()
        for cwe_findings in findings.values()
        for finding in cwe_findings
    ]

    return {
        "target": {
            "repo": environ.get("GITHUB_REPOSITORY", root.name),
            "commit": environ.get("GITHUB_SHA", "workspace"),
            "build": environ.get("GITHUB_RUN_ID", "local"),
        },
        "facts": {
            "cwe_findings": {
                cwe: [finding.as_fact() for finding in cwe_findings]
                for cwe, cwe_findings in findings.items()
            },
            "controls": controls,
        },
        "evidence": evidence,
        "agent": {
            "name": "repo-security-agent",
            "version": "0.1.0",
            "rubric_hint": "asvs.python_secure_coding.v1",
        },
    }


def _collect_findings(root: Path) -> dict[str, list[Finding]]:
    """Collect deterministic findings for the selected CWE set."""
    findings: dict[str, list[Finding]] = {
        "CWE-20": [],
        "CWE-22": [],
        "CWE-78": [],
        "CWE-400": [],
        "CWE-532": [],
        "CWE-862": [],
        "CWE-918": [],
    }

    findings["CWE-20"].extend(
        [
            _finding_for_literal(
                root,
                "CWE-20",
                Path("reqif_mcp/reqif_parser.py"),
                "ET.parse(",
                "ReqIF XML is parsed without an explicit artifact size guard or parser hardening boundary.",
            ),
            _finding_for_literal(
                root,
                "CWE-20",
                Path("reqif_ingest_cli/docling_adapter.py"),
                "DocumentConverter(",
                "Docling conversion is invoked without a preflight size or page-count gate for untrusted documents.",
            ),
            _finding_for_literal(
                root,
                "CWE-20",
                Path("reqif_ingest_cli/xlsx_extractor.py"),
                "load_workbook(",
                "Workbook ingestion does not enforce an explicit row, sheet, or workbook size limit before parsing.",
            ),
        ]
    )

    findings["CWE-22"].extend(
        [
            _finding_for_literal(
                root,
                "CWE-22",
                Path("reqif_mcp/server.py"),
                "log_path = Path(log_file)",
                "Verification log writes accept a caller-provided path without a containment check.",
            ),
            _finding_for_literal(
                root,
                "CWE-22",
                Path("reqif_mcp/decision_logger.py"),
                "log_file_path = Path(log_file_path)",
                "Decision log writes accept an arbitrary path without restricting writes to an evidence root.",
            ),
        ]
    )

    findings["CWE-78"].extend(_scan_command_injection(root))

    findings["CWE-400"].extend(
        [
            _finding_for_literal(
                root,
                "CWE-400",
                Path("reqif_ingest_cli/docling_adapter.py"),
                "DocumentConverter(",
                "Document conversion accepts untrusted PDFs without a size or page-count limit, increasing resource exhaustion risk.",
            ),
            _finding_for_literal(
                root,
                "CWE-400",
                Path("reqif_ingest_cli/xlsx_extractor.py"),
                "load_workbook(",
                "Workbook ingestion lacks a pre-parse row or workbook size limit for resource exhaustion protection.",
            ),
            _finding_for_literal(
                root,
                "CWE-400",
                Path("reqif_mcp/reqif_parser.py"),
                "ET.parse(",
                "ReqIF parsing has no explicit payload size ceiling before XML processing begins.",
            ),
        ]
    )

    findings["CWE-532"].append(
        _finding_for_literal(
            root,
            "CWE-532",
            Path(".github/workflows/compliance-gate.yml"),
            "cat agent_facts.json",
            "The workflow prints the full agent facts payload to CI logs, which risks exposing sensitive evidence or tokens.",
            severity="medium",
        )
    )

    findings["CWE-862"].extend(
        [
            _finding_for_literal(
                root,
                "CWE-862",
                Path("reqif_mcp/server.py"),
                'mcp = FastMCP("reqif-mcp", version="0.1.0")',
                "The FastMCP server is initialized without an authentication or authorization boundary.",
            ),
            _finding_for_literal(
                root,
                "CWE-862",
                Path("reqif_mcp/__main__.py"),
                'mcp.run(transport="http", host=host, port=port)',
                "HTTP transport can be enabled without any access-control enforcement for the exposed tools.",
            ),
        ]
    )

    if _repo_has_remote_fetch_capability(root):
        findings["CWE-918"].append(
            Finding(
                cwe="CWE-918",
                message=(
                    "Repository code performs outbound fetches without an explicit protocol or domain allowlist. "
                    "Review remote-call sites before enabling untrusted URL ingestion."
                ),
                path="reqif_ingest_cli/foundry_adapter.py",
                line=_find_line(root / "reqif_ingest_cli/foundry_adapter.py", "endpoint=config.endpoint"),
                severity="medium",
            )
        )

    return {cwe: [finding for finding in cwe_findings if finding.path] for cwe, cwe_findings in findings.items()}


def _collect_controls(root: Path) -> dict[str, bool]:
    """Collect SSDF-oriented process controls from repo state."""
    justfile = _safe_read(root / "justfile")
    workflow = _safe_read(root / ".github/workflows/compliance-gate.yml")

    return {
        "toolchain_security_tools_defined": all(
            token in justfile for token in ["lint:", "typecheck:", "test:", "check:"]
        ) and "reqif_mcp.compliance_gate" in workflow,
        "secure_coding_baselines_present": all(
            (root / path).exists()
            for path in [
                "samples/standards/derived/owasp_asvs_cwe.reqif",
                "samples/standards/derived/nist_ssdf_dogfood.reqif",
                "opa-bundles/owasp-asvs-sample/.manifest",
                "opa-bundles/nist-ssdf-sample/.manifest",
            ]
        ),
        "code_analysis_findings_recorded": all(
            token in workflow
            for token in [
                "compliance_summary.json",
                "compliance_results.json",
                "upload-artifact",
                "createComment",
            ]
        ),
        "repo_vulnerability_scan_task_present": all(
            _just_recipe_exists(justfile, recipe_name)
            for recipe_name in ["dogfood-asvs", "dogfood-ssdf", "dogfood-asvs-cwe"]
        ) and (root / "agents/repo_security_agent.py").exists(),
        "vulnerability_disclosure_policy_present": any(
            (root / candidate).exists()
            for candidate in ["SECURITY.md", ".github/SECURITY.md", ".well-known/security.txt"]
        ),
        "remote_fetch_capability_present": _repo_has_remote_fetch_capability(root),
        "remote_fetch_allowlist_present": False,
    }


def _scan_command_injection(root: Path) -> list[Finding]:
    """Find shell-based command execution in Python files."""
    findings: list[Finding] = []
    for path in root.rglob("*.py"):
        if any(part in {".venv", ".git", ".uv-cache"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        relative_path = str(path.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func) in {"os.system", "os.popen", "subprocess.call", "subprocess.run", "subprocess.Popen"}:
                if _has_shell_true(node) or _call_name(node.func) in {"os.system", "os.popen"}:
                    findings.append(
                        Finding(
                            cwe="CWE-78",
                            message="Shell-based process execution is present and should be constrained or removed.",
                            path=relative_path,
                            line=getattr(node, "lineno", 1),
                        )
                    )
    return findings


def _repo_has_remote_fetch_capability(root: Path) -> bool:
    """Check whether app code performs remote requests under configurable endpoints."""
    foundry_adapter = _safe_read(root / "reqif_ingest_cli/foundry_adapter.py")
    return "ChatCompletionsClient(" in foundry_adapter and "endpoint=config.endpoint" in foundry_adapter


def _call_name(node: ast.AST) -> str:
    """Resolve a best-effort dotted call name from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _has_shell_true(node: ast.Call) -> bool:
    """Return True when a call uses shell=True."""
    for keyword in node.keywords:
        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
            return bool(keyword.value.value)
    return False


def _finding_for_literal(
    root: Path,
    cwe: str,
    relative_path: Path,
    needle: str,
    message: str,
    severity: str = "high",
) -> Finding:
    """Create a finding for a literal match."""
    absolute_path = root / relative_path
    return Finding(
        cwe=cwe,
        message=message,
        path=str(relative_path),
        line=_find_line(absolute_path, needle),
        severity=severity,
    )


def _find_line(path: Path, needle: str) -> int:
    """Find the first 1-based line number containing a substring."""
    text = _safe_read(path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return line_number
    return 1


def _safe_read(path: Path) -> str:
    """Read a file as UTF-8, returning an empty string on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _just_recipe_exists(justfile: str, recipe_name: str) -> bool:
    """Return True when a Just recipe is defined, with or without parameters."""
    prefixes = (f"{recipe_name}:", f"{recipe_name} ")
    return any(line.startswith(prefixes) for line in justfile.splitlines())


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Deterministic repo-security agent")
    parser.add_argument("--root", default=".", help="Repository root to analyze")
    args = parser.parse_args()
    payload = build_repo_security_facts(Path(args.root).resolve())
    json.dump(payload, fp=sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
