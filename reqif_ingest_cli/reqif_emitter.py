"""Minimal ReqIF emission from deterministic candidates."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

from returns.result import Failure, Result, Success

from reqif_ingest_cli.models import RequirementCandidate, SourceAnchor
from reqif_ingest_cli.utils import json_dumps, stable_id

_ATTRIBUTE_DEFINITIONS: list[tuple[str, str]] = [
    ("attr-key", "Key"),
    ("attr-text", "Text"),
    ("attr-section", "Section"),
    ("attr-subtypes", "SubtypeHints"),
    ("attr-artifact-hash", "ArtifactHash"),
    ("attr-profile", "Profile"),
    ("attr-rule", "ExtractionRule"),
    ("attr-source-anchors", "SourceAnchors"),
    ("attr-metadata-json", "MetadataJson"),
]


def emit_reqif_xml(
    candidates: Sequence[RequirementCandidate],
    title: str,
    comment: str | None = None,
) -> Result[str, Exception]:
    """Emit a small ReqIF baseline from derived candidates."""
    try:
        root = ET.Element("REQ-IF")
        header = ET.SubElement(
            root,
            "REQ-IF-HEADER",
            IDENTIFIER=stable_id("reqif-header", title, len(candidates)),
        )
        ET.SubElement(header, "TITLE").text = title
        if comment:
            ET.SubElement(header, "COMMENT").text = comment

        content = ET.SubElement(root, "REQ-IF-CONTENT")
        spec_types = ET.SubElement(content, "SPEC-TYPES")
        spec_object_type = ET.SubElement(
            spec_types,
            "SPEC-OBJECT-TYPE",
            {
                "IDENTIFIER": "reqif-ingest-type-1",
                "LONG-NAME": "Derived Requirement",
            },
        )
        spec_attributes = ET.SubElement(spec_object_type, "SPEC-ATTRIBUTES")
        for attribute_id, long_name in _ATTRIBUTE_DEFINITIONS:
            ET.SubElement(
                spec_attributes,
                "ATTRIBUTE-DEFINITION-STRING",
                {
                    "IDENTIFIER": attribute_id,
                    "LONG-NAME": long_name,
                },
            )

        spec_objects = ET.SubElement(content, "SPEC-OBJECTS")
        for candidate in candidates:
            _append_spec_object(spec_objects, candidate)

        ET.indent(root, space="  ")
        xml_body = ET.tostring(root, encoding="unicode")
        return Success(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}')
    except Exception as exc:
        return Failure(exc)


def write_reqif_xml(path: str | Path, xml_text: str) -> Result[Path, Exception]:
    """Persist a ReqIF XML document."""
    try:
        output_path = Path(path).expanduser().resolve()
        output_path.write_text(xml_text, encoding="utf-8")
        return Success(output_path)
    except Exception as exc:
        return Failure(exc)


def _append_spec_object(parent: ET.Element, candidate: RequirementCandidate) -> None:
    """Append a candidate as a ReqIF SPEC-OBJECT."""
    spec_object = ET.SubElement(parent, "SPEC-OBJECT", IDENTIFIER=candidate.candidate_id)
    spec_object_type = ET.SubElement(spec_object, "TYPE")
    ET.SubElement(spec_object_type, "SPEC-OBJECT-TYPE-REF").text = "reqif-ingest-type-1"

    values = ET.SubElement(spec_object, "VALUES")
    attribute_values = {
        "attr-key": candidate.key,
        "attr-text": candidate.text,
        "attr-section": candidate.section or "",
        "attr-subtypes": ", ".join(candidate.subtype_hints),
        "attr-artifact-hash": candidate.artifact_sha256,
        "attr-profile": candidate.profile,
        "attr-rule": candidate.extraction_rule_id,
        "attr-source-anchors": _format_anchors(candidate.anchors),
        "attr-metadata-json": json_dumps(candidate.metadata),
    }
    for attribute_id, value in attribute_values.items():
        _append_string_value(values, attribute_id, value)


def _append_string_value(parent: ET.Element, attribute_id: str, value: str) -> None:
    """Append a ReqIF ATTRIBUTE-VALUE-STRING element."""
    attribute_value = ET.SubElement(parent, "ATTRIBUTE-VALUE-STRING")
    definition = ET.SubElement(attribute_value, "DEFINITION")
    ET.SubElement(definition, "ATTRIBUTE-DEFINITION-STRING-REF").text = attribute_id
    ET.SubElement(attribute_value, "THE-VALUE").text = value


def _format_anchors(anchors: Sequence[SourceAnchor]) -> str:
    """Create a compact anchor string for ReqIF storage."""
    parts: list[str] = []
    for anchor in anchors:
        fragment = [
            f"kind={anchor.kind}",
            f"page={anchor.page}" if anchor.page is not None else "",
            f"sheet={anchor.sheet}" if anchor.sheet else "",
            f"row={anchor.row}" if anchor.row is not None else "",
            f"column={anchor.column}" if anchor.column else "",
            f"cell={anchor.cell}" if anchor.cell else "",
            f"paragraph={anchor.paragraph}" if anchor.paragraph is not None else "",
            f"semantic_id={anchor.semantic_id}" if anchor.semantic_id else "",
        ]
        if anchor.heading_path:
            fragment.append(f"heading_path={' > '.join(anchor.heading_path)}")
        parts.append(";".join(value for value in fragment if value))
    return " | ".join(parts)
