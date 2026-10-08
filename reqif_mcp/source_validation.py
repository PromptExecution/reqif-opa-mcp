"""Bounded, offline ReqIF XSD preflight before lossy AST/lookup construction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from io import BytesIO
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import xmlschema
import reqif
from returns.result import Failure, Result, Success

MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_SOURCE_ELEMENTS = 100_000
MAX_SOURCE_DEPTH = 128
MAX_VALIDATION_ISSUES = 64
_SCHEMAS = Path(reqif.__file__).with_name("reqif_schema")
_MANIFEST = Path(__file__).with_name("source_schema_manifest.json")


@dataclass(frozen=True)
class ReqIFSourceIssue:
    kind: Literal["invalid", "unsupported", "unavailable"]
    path: str
    reason: str


class ReqIFSourceValidationError(Exception):
    """Machine-readable preflight failures; not a successful fidelity report."""

    def __init__(self, issues: tuple[ReqIFSourceIssue, ...]) -> None:
        self.issues = issues
        super().__init__(issues[0].reason if issues else "ReqIF validation failed")

    def to_dict(self) -> dict[str, object]:
        return {"issues": [asdict(issue) for issue in self.issues]}


@dataclass(frozen=True)
class ValidatedReqIFSource:
    """Original bytes and exact schema identity, without semantic import claims."""

    original_bytes: bytes
    source_digest: str
    schema_digest: str
    validator_version: str


def _digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _failure(
    kind: Literal["invalid", "unsupported", "unavailable"], reason: str
) -> Failure[ReqIFSourceValidationError]:
    return Failure(
        ReqIFSourceValidationError((ReqIFSourceIssue(kind, "/", reason[:2048]),))
    )


def _schema() -> tuple[xmlschema.XMLSchema, str]:
    """Verify pinned resources before compiling; never consult document hints."""
    manifest_bytes = _MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError("invalid schema manifest")
    if manifest.get("package") != "reqif" or manifest.get("version") != version(
        "reqif"
    ):
        raise ValueError("unsupported schema source revision")
    files = manifest["files"]
    actual = {str(path.relative_to(_SCHEMAS)) for path in _SCHEMAS.rglob("*.xsd")}
    if "reqif.xsd" not in files or set(files) != actual:
        raise ValueError("schema resource set mismatch")
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError("invalid schema manifest entry")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("invalid schema manifest path")
        if _digest((_SCHEMAS / path).read_bytes()) != expected:
            raise ValueError(f"schema resource digest mismatch: {name}")
    schema = xmlschema.XMLSchema(
        _SCHEMAS / "reqif.xsd",
        allow="local",
        defuse="always",
        use_fallback=False,
        use_location_hints=False,
    )
    return schema, _digest(manifest_bytes)


def validate_reqif_source(
    content: bytes,
) -> Result[ValidatedReqIFSource, ReqIFSourceValidationError]:
    """Check supplied bytes with the pinned XSD; no URLs or source paths accepted.

    Successful preflight permits later AST construction. Type/reference closure,
    mapping profiles, parser-warning checks and edited export are separate gates.
    """
    if not isinstance(content, bytes):
        return _failure("invalid", "ReqIF source must be bytes")
    if len(content) > MAX_SOURCE_BYTES:
        return _failure("unsupported", "ReqIF source byte limit exceeded")
    try:
        # Passing a byte stream prevents URL/path input classification. Defusing
        # forbids entity declarations; resource loading and schema hints are off.
        resource = xmlschema.XMLResource(
            BytesIO(content), allow="none", defuse="always", lazy=False
        )
        stack = [(resource.root, 1)]
        count = 0
        while stack:
            element, depth = stack.pop()
            count += 1
            if count > MAX_SOURCE_ELEMENTS or depth > MAX_SOURCE_DEPTH:
                return _failure("unsupported", "ReqIF source structure limit exceeded")
            stack.extend((child, depth + 1) for child in element)
    except (xmlschema.XMLResourceError, ValueError) as exception:
        return _failure("invalid", f"Invalid ReqIF XML: {exception}")
    try:
        schema, schema_digest = _schema()
    except (OSError, ValueError, xmlschema.XMLSchemaException) as exception:
        return _failure("unavailable", f"Pinned ReqIF schema unavailable: {exception}")
    issues: list[ReqIFSourceIssue] = []
    try:
        for error in schema.iter_errors(
            resource, use_defaults=False, use_location_hints=False
        ):
            issues.append(
                ReqIFSourceIssue(
                    "invalid", (error.path or "/")[:1024], str(error.reason)[:2048]
                )
            )
            if len(issues) == MAX_VALIDATION_ISSUES:
                break
    except (xmlschema.XMLSchemaException, ValueError) as exception:
        return _failure("invalid", f"ReqIF schema validation failed: {exception}")
    if issues:
        return Failure(ReqIFSourceValidationError(tuple(issues)))
    return Success(
        ValidatedReqIFSource(
            original_bytes=content,
            source_digest=_digest(content),
            schema_digest=schema_digest,
            validator_version=f"xmlschema:{xmlschema.__version__}",
        )
    )
