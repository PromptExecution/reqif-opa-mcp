"""
ReqIF 1.2 XML Parser Module

Parses ReqIF 1.2 XML documents and extracts SpecObjects, SpecTypes,
AttributeDefinitions, and AttributeValues into a structured format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, TypedDict

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
        # Parse XML
        if isinstance(xml_input, (str, Path)) and Path(xml_input).exists():
            tree = ET.parse(xml_input)
            root = tree.getroot()
        else:
            # Assume it's an XML string
            root = ET.fromstring(str(xml_input))

        # Check if root is REQ-IF element
        if not root.tag.endswith("REQ-IF"):
            return Failure(
                ValueError(f"Invalid ReqIF root element: {root.tag}. Expected REQ-IF")
            )

        # Parse header
        header_result = _parse_header(root)
        if isinstance(header_result, Failure):
            return header_result

        # Parse content
        content_result = _parse_content(root)
        if isinstance(content_result, Failure):
            return content_result

        header = header_result.unwrap()
        content = content_result.unwrap()

        reqif_data: ReqIFData = {
            "header": header,
            "spec_objects": content["spec_objects"],
            "spec_types": content["spec_types"],
            "attribute_definitions": content["attribute_definitions"],
        }

        return Success(reqif_data)

    except ET.ParseError as e:
        return Failure(ValueError(f"Malformed XML: {e}"))
    except Exception as e:
        return Failure(e)


def _parse_header(root: ET.Element) -> Result[ReqIFHeader, Exception]:
    """Parse REQ-IF-HEADER section."""
    try:
        # Find the REQ-IF-HEADER element
        header_elem = root.find(".//REQ-IF-HEADER")
        if header_elem is None:
            return Failure(ValueError("REQ-IF-HEADER element not found"))

        identifier = header_elem.get("IDENTIFIER", "")
        title_elem = header_elem.find(".//TITLE")
        comment_elem = header_elem.find(".//COMMENT")

        title_text = title_elem.text if title_elem is not None and title_elem.text else ""

        header: ReqIFHeader = {
            "identifier": identifier,
            "title": title_text,
            "comment": comment_elem.text if comment_elem is not None else None,
        }

        return Success(header)
    except Exception as e:
        return Failure(e)


class _ContentData(TypedDict):
    """Intermediate content data structure."""

    spec_objects: list[SpecObject]
    spec_types: list[SpecType]
    attribute_definitions: list[AttributeDefinition]


def _parse_content(root: ET.Element) -> Result[_ContentData, Exception]:
    """Parse REQ-IF-CONTENT section."""
    try:
        content_elem = root.find(".//REQ-IF-CONTENT")
        if content_elem is None:
            return Failure(ValueError("REQ-IF-CONTENT element not found"))

        # Parse SpecTypes
        spec_types: list[SpecType] = []
        spec_types_elem = content_elem.find(".//SPEC-TYPES")
        if spec_types_elem is not None:
            for spec_type_elem in spec_types_elem.findall(".//SPEC-OBJECT-TYPE"):
                identifier = spec_type_elem.get("IDENTIFIER", "")
                long_name = spec_type_elem.get("LONG-NAME", "")

                # Parse attribute definitions for this spec type
                attr_defs: list[AttributeDefinition] = []
                spec_attrs_elem = spec_type_elem.find(".//SPEC-ATTRIBUTES")
                if spec_attrs_elem is not None:
                    for attr_def_elem in spec_attrs_elem.findall(
                        ".//ATTRIBUTE-DEFINITION-STRING"
                    ):
                        attr_id = attr_def_elem.get("IDENTIFIER", "")
                        attr_long_name = attr_def_elem.get("LONG-NAME", "")
                        attr_defs.append(
                            {
                                "identifier": attr_id,
                                "long_name": attr_long_name,
                                "data_type": "string",
                            }
                        )

                spec_types.append(
                    {
                        "identifier": identifier,
                        "long_name": long_name,
                        "attribute_definitions": attr_defs,
                    }
                )

        # Parse SpecObjects
        spec_objects: list[SpecObject] = []
        spec_objects_elem = content_elem.find(".//SPEC-OBJECTS")
        if spec_objects_elem is not None:
            for spec_obj_elem in spec_objects_elem.findall(".//SPEC-OBJECT"):
                identifier = spec_obj_elem.get("IDENTIFIER", "")

                # Get type reference
                type_elem = spec_obj_elem.find(".//TYPE/SPEC-OBJECT-TYPE-REF")
                spec_type_ref = ""
                if type_elem is not None and type_elem.text:
                    spec_type_ref = type_elem.text

                # Parse attribute values
                attr_values: list[AttributeValue] = []
                values_elem = spec_obj_elem.find(".//VALUES")
                if values_elem is not None:
                    for attr_val_elem in values_elem.findall(
                        ".//ATTRIBUTE-VALUE-STRING"
                    ):
                        def_elem = attr_val_elem.find(".//DEFINITION")
                        def_ref = ""
                        if def_elem is not None:
                            attr_def_ref_elem = def_elem.find(
                                ".//ATTRIBUTE-DEFINITION-STRING-REF"
                            )
                            if (
                                attr_def_ref_elem is not None
                                and attr_def_ref_elem.text
                            ):
                                def_ref = attr_def_ref_elem.text

                        value_elem = attr_val_elem.find(".//THE-VALUE")
                        value = value_elem.text if value_elem is not None else ""

                        attr_values.append({"definition_ref": def_ref, "value": value})

                spec_objects.append(
                    {
                        "identifier": identifier,
                        "spec_type_ref": spec_type_ref,
                        "attributes": attr_values,
                    }
                )

        # Collect all attribute definitions
        all_attr_defs: list[AttributeDefinition] = []
        for spec_type in spec_types:
            all_attr_defs.extend(spec_type["attribute_definitions"])

        return Success(
            {
                "spec_objects": spec_objects,
                "spec_types": spec_types,
                "attribute_definitions": all_attr_defs,
            }
        )
    except Exception as e:
        return Failure(e)
