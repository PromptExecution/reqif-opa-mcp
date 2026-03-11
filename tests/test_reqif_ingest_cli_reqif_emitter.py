"""Tests for ReqIF emission from deterministic candidates."""

from __future__ import annotations

from returns.result import Success

from reqif_ingest_cli.models import RequirementCandidate, SourceAnchor
from reqif_ingest_cli.reqif_emitter import emit_reqif_xml
from reqif_mcp.reqif_parser import parse_reqif_xml


def test_emit_reqif_xml_round_trips_through_existing_parser() -> None:
    """Derived ReqIF should parse through the existing XML parser."""
    candidate = RequirementCandidate(
        schema="requirement_candidate/1",
        candidate_id="candidate-1",
        artifact_id="artifact-1",
        artifact_sha256="sha256-value",
        profile="aescsf_core_v2",
        key="ACCESS-1a",
        text="Identities are provisioned.",
        section="ACCESS-1",
        subtype_hints=["ACCESS", "SP-1"],
        extraction_rule_id="xlsx.aescsf_core.practice_row.v1",
        rationale="Mapped Practice ID and Practice columns from the AESCSF core workbook.",
        confidence_source="deterministic",
        source_node_ids=["row-1", "paragraph-1"],
        anchors=[
            SourceAnchor(
                kind="xlsx_cell_paragraph",
                artifact_id="artifact-1",
                sheet="AESCSF Core",
                row=2,
                column="E",
                cell="E2",
                paragraph=1,
                semantic_id="ACCESS-1a",
            )
        ],
        metadata={"objective_id": "ACCESS-1"},
    )

    result = emit_reqif_xml([candidate], title="Derived AESCSF")

    assert isinstance(result, Success)
    parse_result = parse_reqif_xml(result.unwrap())
    assert isinstance(parse_result, Success)

    reqif_data = parse_result.unwrap()
    assert reqif_data["header"]["title"] == "Derived AESCSF"
    assert len(reqif_data["spec_objects"]) == 1
    assert reqif_data["spec_objects"][0]["identifier"] == "candidate-1"
