"""Schema-valid wrong-category and foreign-type references must not publish."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from returns.result import Failure, Success

from reqif_mcp.source_semantics import validate_reqif_semantics
from reqif_mcp.source_validation import validate_reqif_source

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "reqif_source_semantics.json").read_text()
)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["name"])
def test_category_and_value_closure(case: dict[str, Any]) -> None:
    content = FIXTURE["baseline"]
    for old, new in case["edits"]:
        assert old in content
        content = content.replace(old, new, 1)
    source = content.encode()
    # These cases deliberately satisfy the XSD: that gate alone is insufficient.
    preflight = validate_reqif_source(source)
    assert isinstance(preflight, Success), preflight.failure().to_dict()
    result = validate_reqif_semantics(source)
    if case["valid"]:
        assert isinstance(result, Success), result.failure().to_dict()
        assert result.unwrap().original_bytes == source
        assert b'THE-VALUE="+007"' in result.unwrap().original_bytes
    else:
        assert isinstance(result, Failure)
        assert any(
            case["reason"] in issue.reason and issue.kind == case["kind"]
            for issue in result.failure().issues
        )
