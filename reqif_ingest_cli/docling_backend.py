"""Configurable Docling extraction backend.

Two implementations, same `document_graph/1` output shape:

- ``"b00t"`` (default, preferred): shells out to the standalone
  `b00t-docling-serve <https://github.com/PromptExecution>`_ package
  (`~/.dotfiles/b00t-docling-serve` by default, override via
  ``B00T_DOCLING_SERVE_DIR``) — Docling extraction relocated there
  2026-08-23 so it's an independently-versioned b00t capability rather
  than bundled inside this ReqIF/OPA/SARIF-specific tool.
- ``"local"``: this repo's own in-process
  :mod:`reqif_ingest_cli.docling_adapter`, kept as a fallback / for
  environments where `b00t-docling-serve` isn't installed.

Select via the ``REQIF_DOCLING_BACKEND`` env var, or the ``--backend`` CLI
flag (takes precedence over the env var).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from returns.result import Failure, Result, Success

from reqif_ingest_cli.docling_adapter import extract_docling_document as _extract_local
from reqif_ingest_cli.models import ArtifactRecord, DocumentGraph, DocumentNode, SourceAnchor

DEFAULT_BACKEND = "b00t"
DEFAULT_B00T_DOCLING_SERVE_DIR = Path("~/.dotfiles/b00t-docling-serve").expanduser()


def extract_docling_document(
    path: str,
    source_uri: str | None = None,
    profile: str = "auto",
    backend: str | None = None,
) -> Result[DocumentGraph, Exception]:
    """Extract via the configured backend (b00t preferred, local fallback)."""
    resolved_backend = backend or os.environ.get("REQIF_DOCLING_BACKEND", DEFAULT_BACKEND)
    if resolved_backend == "local":
        return _extract_local(path, source_uri=source_uri, profile=profile)
    if resolved_backend == "b00t":
        return _extract_via_b00t(path, source_uri=source_uri, profile=profile)
    return Failure(
        ValueError(f"Unknown docling backend: {resolved_backend!r} (expected 'b00t' or 'local')")
    )


def _extract_via_b00t(
    path: str,
    source_uri: str | None,
    profile: str,
) -> Result[DocumentGraph, Exception]:
    serve_dir = Path(
        os.environ.get("B00T_DOCLING_SERVE_DIR", str(DEFAULT_B00T_DOCLING_SERVE_DIR))
    ).expanduser()
    if not serve_dir.is_dir():
        return Failure(
            FileNotFoundError(
                f"b00t-docling-serve not found at {serve_dir} — install it, set "
                "B00T_DOCLING_SERVE_DIR, or pass --backend local"
            )
        )

    resolved_path = str(Path(path).expanduser().resolve())
    args = ["uv", "run", "python", "-m", "b00t_docling_serve", "extract", resolved_path, "--profile", profile]
    if source_uri:
        args += ["--source-uri", source_uri]

    # Drop VIRTUAL_ENV/uv's active-project markers inherited from the caller
    # (e.g. reqif-opa-mcp's own venv) — this subprocess is a different uv
    # project (b00t-docling-serve) and must resolve its own environment.
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}

    try:
        completed = subprocess.run(
            args,
            cwd=serve_dir,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Failure(RuntimeError(f"failed to run b00t-docling-serve: {exc}"))

    if completed.returncode != 0:
        return Failure(
            RuntimeError(f"b00t-docling-serve exited {completed.returncode}: {completed.stderr.strip()}")
        )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return Failure(RuntimeError(f"b00t-docling-serve produced invalid JSON: {exc}"))

    return Success(_graph_from_dict(payload))


def _graph_from_dict(payload: dict) -> DocumentGraph:
    """Reconstruct a DocumentGraph from its JSON representation."""
    artifact = ArtifactRecord(**payload["artifact"])
    nodes = [
        DocumentNode(
            node_id=n["node_id"],
            node_type=n["node_type"],
            text=n.get("text"),
            parent_id=n.get("parent_id"),
            semantic_id=n.get("semantic_id"),
            attributes=n.get("attributes", {}),
            anchors=[SourceAnchor(**a) for a in n.get("anchors", [])],
        )
        for n in payload["nodes"]
    ]
    return DocumentGraph(
        schema=payload["schema"],
        artifact=artifact,
        profile=payload["profile"],
        nodes=nodes,
        metadata=payload.get("metadata", {}),
    )
