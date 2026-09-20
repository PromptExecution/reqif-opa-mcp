"""
ReqIF 1.2 XML Parser Module

Parses ReqIF 1.2 XML documents and extracts SpecObjects, SpecTypes,
AttributeDefinitions, and AttributeValues into a structured format.

Delegates the actual parsing to the Apache-2.0 StrictDoc `reqif` package
(`reqif.parser.ReqIFParser`) rather than hand-rolling ReqIF XML handling:
`reqif` already implements the full ReqIF 1.2 element model (the standard
`<THE-HEADER><REQ-IF-HEADER>`/`<CORE-CONTENT><REQ-IF-CONTENT>` wrapper
structure, every `SpecObjectAttributeType`, ReqIFz archives), is exercised
against real tool exports, and was already a declared dependency here
(`pyproject.toml`) that nothing in this module actually called. This
module's job is narrowed to one thing: map a `reqif.reqif_bundle.ReqIFBundle`
onto the `ReqIFData` contract the rest of this codebase (server.py, the
normalization/OPA layers, every existing test) already depends on, so that
contract -- not the parsing implementation -- is what downstream code needs
to keep working.
"""

from pathlib import Path
from typing import Any, TypedDict

from lxml.etree import XMLSyntaxError
from reqif.models.error_handling import (
    ReqIFSchemaError,
    ReqIFXMLParsingError,
)
from reqif.models.reqif_spec_object import ReqIFSpecObject as _SDSpecObject
from reqif.models.reqif_spec_object_type import ReqIFSpecObjectType as _SDSpecObjectType
from reqif.parser import ReqIFParser
from reqif.reqif_bundle import ReqIFBundle
from returns.result import Failure, Result, Success


class AttributeValue(TypedDict, total=False):
    """Attribute value in ReqIF."""

    definition_ref: str
    value: Any


class SpecObject(TypedDict):
    """SpecObject represents a requirement in ReqIF."""

    identifier: str
    spec_type_ref: str
    attributes: list[AttributeValue]


class AttributeDefinition(TypedDict):
    """AttributeDefinition defines the structure of attributes."""

    identifier: str
    long_name: str
    data_type: str


class SpecType(TypedDict):
    """SpecType defines the type/template for SpecObjects."""

    identifier: str
    long_name: str
    attribute_definitions: list[AttributeDefinition]


class ReqIFHeader(TypedDict):
    """ReqIF header metadata."""

    identifier: str
    title: str
    comment: str | None


class ReqIFData(TypedDict):
    """Parsed ReqIF data structure."""

    header: ReqIFHeader
    spec_objects: list[SpecObject]
    spec_types: list[SpecType]
    attribute_definitions: list[AttributeDefinition]


def parse_reqif_xml(xml_input: str | Path) -> Result[ReqIFData, Exception]:
    """
    Parse ReqIF 1.2 XML from string or file path.

    Args:
        xml_input: XML string or file path to ReqIF document

    Returns:
        Result containing parsed ReqIFData or Exception
    """
    try:
        # Same input-classification rules the previous hand-rolled parser
        # used: a `Path`, or a string that names an existing file, is read
        # from disk; anything else is treated as raw XML content.
        if isinstance(xml_input, Path):
            content = xml_input.read_text(encoding="UTF-8")
        elif isinstance(xml_input, str):
            if xml_input.strip().startswith("<"):
                content = xml_input
            else:
                path = Path(xml_input)
                content = (
                    path.read_text(encoding="UTF-8") if path.exists() else xml_input
                )
        else:
            return Failure(ValueError(f"Invalid xml_input type: {type(xml_input)}"))

        try:
            bundle = ReqIFParser.parse_from_string(content)
        except ReqIFXMLParsingError as exception:
            message = str(exception)
            if "Expected root tag to be REQ-IF" in message:
                # Preserve this module's own established error wording (all
                # existing callers/tests match on it) while keeping the
                # library's own diagnostic for the actual tag found.
                return Failure(
                    ValueError(
                        f"Invalid ReqIF root element. Expected REQ-IF. ({message})"
                    )
                )
            return Failure(ValueError(f"Malformed XML: {message}"))
        except (XMLSyntaxError, ReqIFSchemaError) as exception:
            return Failure(ValueError(f"Malformed XML: {exception}"))

        return _map_bundle(bundle)
    except Exception as e:  # noqa: BLE001 - surfaced as a typed Failure, not raised
        return Failure(e)


def _map_bundle(bundle: ReqIFBundle) -> Result[ReqIFData, Exception]:
    """Map a parsed `ReqIFBundle` onto this module's `ReqIFData` contract."""
    if bundle.req_if_header is None:
        return Failure(ValueError("REQ-IF-HEADER element not found"))
    header: ReqIFHeader = {
        "identifier": bundle.req_if_header.identifier or "",
        "title": bundle.req_if_header.title or "",
        "comment": bundle.req_if_header.comment,
    }

    if bundle.core_content is None or bundle.core_content.req_if_content is None:
        return Failure(ValueError("REQ-IF-CONTENT element not found"))
    content = bundle.core_content.req_if_content

    spec_types = [
        _map_spec_type(t)
        for t in (content.spec_types or [])
        if isinstance(t, _SDSpecObjectType)
    ]
    spec_objects = [_map_spec_object(o) for o in (content.spec_objects or [])]

    # Flattened across every spec type, same as the previous parser -- a
    # caller that wants a type's own definitions already has
    # `spec_type["attribute_definitions"]`.
    attribute_definitions = [
        attr_def
        for spec_type in spec_types
        for attr_def in spec_type["attribute_definitions"]
    ]

    reqif_data: ReqIFData = {
        "header": header,
        "spec_objects": spec_objects,
        "spec_types": spec_types,
        "attribute_definitions": attribute_definitions,
    }
    return Success(reqif_data)


def _map_spec_type(spec_type: _SDSpecObjectType) -> SpecType:
    attr_defs: list[AttributeDefinition] = [
        {
            "identifier": attr_def.identifier,
            "long_name": attr_def.long_name or "",
            "data_type": attr_def.attribute_type.name.lower(),
        }
        for attr_def in (spec_type.attribute_definitions or [])
    ]
    return {
        "identifier": spec_type.identifier,
        "long_name": spec_type.long_name or "",
        "attribute_definitions": attr_defs,
    }


def _map_spec_object(spec_object: _SDSpecObject) -> SpecObject:
    attributes: list[AttributeValue] = [
        {"definition_ref": attr.definition_ref, "value": attr.value}
        for attr in (spec_object.attributes or [])
    ]
    return {
        "identifier": spec_object.identifier,
        "spec_type_ref": spec_object.spec_object_type or "",
        "attributes": attributes,
    }
