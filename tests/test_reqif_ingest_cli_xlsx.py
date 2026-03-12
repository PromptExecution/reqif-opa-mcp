"""Tests for deterministic XLSX extraction and distillation."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from returns.result import Success

from reqif_ingest_cli.xlsx_extractor import distill_xlsx_requirements, extract_xlsx_document


def test_extract_aescsf_core_profile_and_paragraph_chunking(tmp_path: Path) -> None:
    """Core workbook extraction should detect the profile and preserve paragraph anchors."""
    path = tmp_path / "aescsf-core.xlsx"
    _write_core_workbook(path)

    result = extract_xlsx_document(path)

    assert isinstance(result, Success)
    graph = result.unwrap()
    assert graph.profile == "aescsf_core_v2"

    paragraph_nodes = [
        node
        for node in graph.nodes
        if node.node_type == "paragraph" and node.attributes.get("role") == "context_guidance"
    ]
    assert len(paragraph_nodes) == 2
    first_anchor = paragraph_nodes[0].anchors[0]
    second_anchor = paragraph_nodes[1].anchors[0]
    assert first_anchor.cell == "F2"
    assert first_anchor.paragraph == 1
    assert second_anchor.cell == "F2"
    assert second_anchor.paragraph == 2


def test_distill_aescsf_core_candidates(tmp_path: Path) -> None:
    """Core workbook distillation should create deterministic requirement candidates."""
    path = tmp_path / "aescsf-core.xlsx"
    _write_core_workbook(path)

    result = distill_xlsx_requirements(path)

    assert isinstance(result, Success)
    candidates = result.unwrap()
    assert [candidate.key for candidate in candidates] == ["ACCESS-1a", "ACCESS-1b"]
    assert candidates[0].section == "ACCESS-1"
    assert candidates[0].metadata["objective"] == "Establish Identities and Manage Authentication"
    assert candidates[0].metadata["context_guidance"] == [
        "Provisioning must be tracked.",
        "Records should be reviewed quarterly.",
    ]


def test_distill_aescsf_toolkit_candidates(tmp_path: Path) -> None:
    """Toolkit sheets should be parsed as row-based practices with context guidance."""
    path = tmp_path / "aescsf-toolkit.xlsx"
    _write_toolkit_workbook(path)

    result = distill_xlsx_requirements(path)

    assert isinstance(result, Success)
    candidates = result.unwrap()
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.profile == "aescsf_toolkit_v1_1"
    assert candidate.key == "ACCESS-1a"
    assert candidate.section == "ACCESS-1"
    assert candidate.metadata["objective"] == "Establish Identities and Manage Authentication"
    assert candidate.metadata["context_guidance"] == [
        "Provisioning shall be approved before access is granted.",
        "Evidence should be retained.",
    ]


def _write_core_workbook(path: Path) -> None:
    """Create a small AESCSF core fixture workbook."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "AESCSF Core"
    worksheet.append(
        [
            "Domain",
            "Objective ID",
            "Objective",
            "Practice ID",
            "Practice",
            "Context and Guidance",
            "Maturity Indicator Level",
            "Security Profile",
        ]
    )
    worksheet.append(
        [
            "ACCESS",
            "ACCESS-1",
            "Establish Identities and Manage Authentication",
            "ACCESS-1a",
            "Identities are provisioned.",
            "Provisioning must be tracked.\n\nRecords should be reviewed quarterly.",
            "MIL-1",
            "SP-1",
        ]
    )
    worksheet.append(
        [
            "ACCESS",
            "ACCESS-1",
            "Establish Identities and Manage Authentication",
            "ACCESS-1b",
            "Credentials are issued before access.",
            "",
            "MIL-1",
            "SP-1",
        ]
    )
    workbook.save(path)


def _write_toolkit_workbook(path: Path) -> None:
    """Create a small AESCSF toolkit fixture workbook."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "ACCESS-1"
    worksheet["D2"] = "ACCESS-1"
    worksheet["D3"] = "Establish Identities and Manage Authentication"
    worksheet["D4"] = "Practices"
    worksheet["A8"] = "ACCESS-1a"
    worksheet["D8"] = "Identities are provisioned."
    worksheet["J8"] = "MIL-1"
    worksheet["L8"] = "SP-1"
    worksheet["D10"] = "Context and Guidance"
    worksheet["D11"] = "Provisioning shall be approved before access is granted.\n\nEvidence should be retained."
    workbook.save(path)
