"""Integrity errors distinguish missing evidence from invalid scalar types."""

import json
from pathlib import Path
from typing import Any

import pytest

from reqif_mcp.validation import validate_requirement_integrity


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).parent / "fixtures/policy_baseline_values.json").read_text()),
)
def test_policy_baseline_value_diagnostics(case: dict[str, Any]) -> None:
    """Reject invalid values without classifying an empty string as a wrong type."""
    record = {
        "uid": "REQ-1",
        "policy_baseline": {"id": case["value"], "version": "1", "hash": "recorded"},
        "rubrics": [],
    }
    result = validate_requirement_integrity([record]).unwrap()
    assert result["valid"] is False
    assert len(result["errors"]) == 1
    assert result["errors"][0]["field"] == "policy_baseline.id"
    assert case["message"] in result["errors"][0]["message"]
