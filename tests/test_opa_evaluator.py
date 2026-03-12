"""Tests for OPA evaluator diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from returns.result import Failure

from reqif_mcp.opa_evaluator import evaluate_with_opa


def test_evaluate_with_opa_surfaces_stdout_errors(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """OPA loader errors emitted on stdout should appear in the failure message."""
    bundle_path = tmp_path / "bundle"
    bundle_path.mkdir()

    class CompletedProcess:
        """Minimal completed-process test double."""

        returncode = 2
        stdout = '{"errors":[{"message":"rego_parse_error: bad policy"}]}'
        stderr = ""

    monkeypatch.setattr(
        "reqif_mcp.opa_evaluator.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(),
    )

    result = evaluate_with_opa(
        opa_input={"requirement": {}, "facts": {}, "context": {}},
        bundle_path=bundle_path,
        package="example.policy.v1",
        rule="decision",
        opa_binary="opa",
    )

    assert isinstance(result, Failure)
    assert "rego_parse_error" in str(result.failure())
