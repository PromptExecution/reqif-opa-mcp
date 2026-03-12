"""Tests for artifact registration."""

from __future__ import annotations

import hashlib
from pathlib import Path

from returns.result import Failure, Success

from reqif_ingest_cli.artifact import register_artifact


def test_register_artifact_hashes_local_file(tmp_path: Path) -> None:
    """Artifact intake should preserve immutable file metadata."""
    path = tmp_path / "policy.xlsx"
    payload = b"deterministic artifact bytes"
    path.write_bytes(payload)

    result = register_artifact(
        path,
        source_uri="https://example.test/policy.xlsx",
        document_profile="generic_xlsx_table",
    )

    assert isinstance(result, Success)
    artifact = result.unwrap()
    assert artifact.sha256 == hashlib.sha256(payload).hexdigest()
    assert artifact.file_format == "xlsx"
    assert artifact.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert artifact.source_uri == "https://example.test/policy.xlsx"
    assert artifact.document_profile == "generic_xlsx_table"
    assert artifact.source_path == str(path.resolve())
    assert artifact.artifact_id.startswith("artifact-")


def test_register_artifact_rejects_missing_path(tmp_path: Path) -> None:
    """Artifact intake should fail cleanly for missing files."""
    result = register_artifact(tmp_path / "missing.pdf")

    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, FileNotFoundError)
    assert "Artifact not found" in str(error)
