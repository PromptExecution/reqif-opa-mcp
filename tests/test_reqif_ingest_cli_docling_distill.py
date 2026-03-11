"""Tests for generic Docling graph distillation."""

from __future__ import annotations

from reqif_ingest_cli.docling_adapter import distill_docling_graph
from reqif_ingest_cli.models import ArtifactRecord, DocumentGraph, DocumentNode, SourceAnchor


def test_distill_docling_graph_selects_modal_paragraphs() -> None:
    """Only normative paragraphs should become candidates."""
    artifact = ArtifactRecord(
        schema="artifact/1",
        artifact_id="artifact-123",
        sha256="abc123",
        filename="overview.pdf",
        source_path="/tmp/overview.pdf",
        source_uri=None,
        media_type="application/pdf",
        file_format="pdf",
        size_bytes=10,
        ingested_at="2026-03-11T00:00:00Z",
        document_profile="pdf_docling_v1",
    )
    graph = DocumentGraph(
        schema="document_graph/1",
        artifact=artifact,
        profile="pdf_docling_v1",
        nodes=[
            DocumentNode(
                node_id="paragraph-1",
                node_type="paragraph",
                text="The operator must retain evidence for each assessment.",
                parent_id=None,
                semantic_id="req-a",
                attributes={"label": "paragraph"},
                anchors=[
                    SourceAnchor(
                        kind="docling_paragraph",
                        artifact_id=artifact.artifact_id,
                        page=3,
                        paragraph=1,
                        heading_path=["Assessment"],
                        semantic_id="req-a",
                    )
                ],
            ),
            DocumentNode(
                node_id="paragraph-2",
                node_type="paragraph",
                text="This overview explains the assessment workflow.",
                parent_id=None,
                semantic_id="info-a",
                attributes={"label": "paragraph"},
                anchors=[
                    SourceAnchor(
                        kind="docling_paragraph",
                        artifact_id=artifact.artifact_id,
                        page=3,
                        paragraph=2,
                        heading_path=["Assessment"],
                        semantic_id="info-a",
                    )
                ],
            ),
        ],
    )

    candidates = distill_docling_graph(graph)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.text == "The operator must retain evidence for each assessment."
    assert candidate.section == "Assessment"
    assert candidate.extraction_rule_id == "docling.modal_paragraph.v1"
