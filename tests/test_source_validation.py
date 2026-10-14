"""Preflight must reject silent-loss cases before mature parser construction."""

from __future__ import annotations

import hashlib
import json
import shutil
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from returns.result import Failure, Success

from reqif_mcp import source_validation

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "reqif_source_validation.json").read_text()
)


def content_for(case: dict[str, Any]) -> bytes:
    content = FIXTURE["baseline"]
    for original, replacement in case.get("edits", []):
        assert original in content
        content = content.replace(original, replacement, 1)
    if "padding" in case:
        content += " " * case["padding"]
    if "depth" in case:
        content = "<n>" * case["depth"] + "</n>" * case["depth"]
    return content.encode("utf-8")


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["name"])
def test_schema_preflight(case: dict[str, Any]) -> None:
    content = content_for(case)
    result = source_validation.validate_reqif_source(content)
    if case["valid"]:
        assert isinstance(result, Success), result.failure().to_dict()
        source = result.unwrap()
        assert source.original_bytes == content
        assert source.source_digest == "sha256:" + hashlib.sha256(content).hexdigest()
        assert source.schema_digest.startswith("sha256:")
        assert source.validator_version == "xmlschema:4.3.1"
    else:
        assert isinstance(result, Failure)
        failure = result.failure()
        assert failure.issues[0].kind == case.get("kind", "invalid")
        assert failure.to_dict()["issues"]


def test_missing_or_corrupt_schema_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = FIXTURE["baseline"].encode()
    resource_root = source_validation._SCHEMAS
    monkeypatch.setattr(source_validation, "_SCHEMAS", tmp_path / "schemas")
    missing = source_validation.validate_reqif_source(content)
    assert isinstance(missing, Failure)
    assert missing.failure().issues[0].kind == "unavailable"
    shutil.copytree(resource_root, tmp_path / "schemas")
    (tmp_path / "schemas" / "reqif.xsd").write_bytes(b"corrupt schema")
    corrupt = source_validation.validate_reqif_source(content)
    assert isinstance(corrupt, Failure)
    assert "digest mismatch" in corrupt.failure().issues[0].reason


def test_concurrent_validation_preserves_cwd_and_result_identity() -> None:
    original_cwd = Path.cwd()
    cases = [case for case in FIXTURE["cases"] if "padding" not in case]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                source_validation.validate_reqif_source, map(content_for, cases)
            )
        )
    assert Path.cwd() == original_cwd
    for case, result in zip(cases, results, strict=True):
        assert isinstance(result, Success) == case["valid"], case["name"]


def test_element_limit_fails_before_schema_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(source_validation, "MAX_SOURCE_ELEMENTS", 2)
    result = source_validation.validate_reqif_source(FIXTURE["baseline"].encode())
    assert isinstance(result, Failure)
    assert result.failure().issues[0].kind == "unsupported"


def test_schema_hints_cannot_open_network_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_connection(*args: object, **kwargs: object) -> None:
        pytest.fail("source validation attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", unexpected_connection)
    for case in FIXTURE["cases"]:
        if case["name"].startswith("ignored_"):
            assert isinstance(
                source_validation.validate_reqif_source(content_for(case)), Success
            )


def test_filename_input_is_rejected() -> None:
    result = source_validation.validate_reqif_source("file:///tmp/private")  # type: ignore[arg-type]
    assert isinstance(result, Failure)
    assert result.failure().issues[0].kind == "invalid"
