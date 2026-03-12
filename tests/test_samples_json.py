"""Tests for JSON fixtures referenced by the README."""

from __future__ import annotations

import json
from pathlib import Path


def test_contract_samples_are_valid_json() -> None:
    """All tracked contract samples should parse as JSON."""
    contract_dir = Path("samples/contracts")
    sample_files = sorted(contract_dir.glob("*.json"))

    assert sample_files
    for sample_file in sample_files:
        payload = json.loads(sample_file.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), sample_file


def test_contract_samples_cover_core_readme_examples() -> None:
    """The README-linked sample set should cover the main interfaces."""
    contract_dir = Path("samples/contracts")
    expected = {
        "agent-facts.example.json": "facts",
        "opa-output.example.json": "status",
        "requirement-candidate.example.json": "schema",
        "requirement-record.example.json": "uid",
    }

    for filename, key in expected.items():
        payload = json.loads((contract_dir / filename).read_text(encoding="utf-8"))
        assert key in payload, filename
