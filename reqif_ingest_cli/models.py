"""Typed models for artifact intake, structural extraction, and distillation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ArtifactRecord:
    """Immutable metadata for a source artifact."""

    schema: str
    artifact_id: str
    sha256: str
    filename: str
    source_path: str
    source_uri: str | None
    media_type: str
    file_format: str
    size_bytes: int
    ingested_at: str
    document_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping."""
        return asdict(self)


@dataclass(slots=True)
class SourceAnchor:
    """Format-specific provenance anchor."""

    kind: str
    artifact_id: str
    page: int | None = None
    sheet: str | None = None
    row: int | None = None
    column: str | None = None
    cell: str | None = None
    paragraph: int | None = None
    heading_path: list[str] = field(default_factory=list)
    semantic_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping."""
        return asdict(self)


@dataclass(slots=True)
class DocumentNode:
    """Canonical document graph node."""

    node_id: str
    node_type: str
    text: str | None
    parent_id: str | None
    semantic_id: str | None
    attributes: dict[str, Any] = field(default_factory=dict)
    anchors: list[SourceAnchor] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping."""
        return asdict(self)


@dataclass(slots=True)
class DocumentGraph:
    """Intermediate representation between raw artifacts and derived ReqIF."""

    schema: str
    artifact: ArtifactRecord
    profile: str
    nodes: list[DocumentNode]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping."""
        return asdict(self)


@dataclass(slots=True)
class RequirementCandidate:
    """Deterministically derived requirement candidate."""

    schema: str
    candidate_id: str
    artifact_id: str
    artifact_sha256: str
    profile: str
    key: str
    text: str
    section: str | None
    subtype_hints: list[str]
    extraction_rule_id: str
    rationale: str
    confidence_source: str
    source_node_ids: list[str] = field(default_factory=list)
    anchors: list[SourceAnchor] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping."""
        return asdict(self)
