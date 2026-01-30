"""
Unit tests for ReqIF 1.2 XML parser module.

Tests cover:
- Parsing well-formed ReqIF XML successfully
- Rejecting malformed XML with clear errors
- Handling invalid references in ReqIF (missing SpecType)
- Handling empty ReqIF (no SpecObjects) without error
"""

from pathlib import Path

import pytest
from returns.result import Failure, Success

from reqif_mcp.reqif_parser import parse_reqif_xml


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_well_formed_reqif_xml() -> None:
    """Test parsing well-formed ReqIF XML successfully."""

    # Well-formed ReqIF XML with minimal structure
    well_formed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Test Baseline</TITLE>
    <COMMENT>Test comment</COMMENT>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES>
      <SPEC-OBJECT-TYPE IDENTIFIER="type-001" LONG-NAME="Requirement Type">
        <SPEC-ATTRIBUTES>
          <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="attr-001" LONG-NAME="Key"/>
          <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="attr-002" LONG-NAME="Text"/>
        </SPEC-ATTRIBUTES>
      </SPEC-OBJECT-TYPE>
    </SPEC-TYPES>
    <SPEC-OBJECTS>
      <SPEC-OBJECT IDENTIFIER="req-001">
        <TYPE>
          <SPEC-OBJECT-TYPE-REF>type-001</SPEC-OBJECT-TYPE-REF>
        </TYPE>
        <VALUES>
          <ATTRIBUTE-VALUE-STRING>
            <DEFINITION>
              <ATTRIBUTE-DEFINITION-STRING-REF>attr-001</ATTRIBUTE-DEFINITION-STRING-REF>
            </DEFINITION>
            <THE-VALUE>REQ-001</THE-VALUE>
          </ATTRIBUTE-VALUE-STRING>
          <ATTRIBUTE-VALUE-STRING>
            <DEFINITION>
              <ATTRIBUTE-DEFINITION-STRING-REF>attr-002</ATTRIBUTE-DEFINITION-STRING-REF>
            </DEFINITION>
            <THE-VALUE>Test requirement text</THE-VALUE>
          </ATTRIBUTE-VALUE-STRING>
        </VALUES>
      </SPEC-OBJECT>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the XML
    result = parse_reqif_xml(well_formed_xml)

    # Assert successful parsing
    assert isinstance(result, Success), f"Expected Success, got Failure: {result}"

    reqif_data = result.unwrap()

    # Validate header
    assert reqif_data["header"]["identifier"] == "header-001"
    assert reqif_data["header"]["title"] == "Test Baseline"
    assert reqif_data["header"]["comment"] == "Test comment"

    # Validate spec types
    assert len(reqif_data["spec_types"]) == 1
    spec_type = reqif_data["spec_types"][0]
    assert spec_type["identifier"] == "type-001"
    assert spec_type["long_name"] == "Requirement Type"
    assert len(spec_type["attribute_definitions"]) == 2

    # Validate attribute definitions
    attr_defs = spec_type["attribute_definitions"]
    assert attr_defs[0]["identifier"] == "attr-001"
    assert attr_defs[0]["long_name"] == "Key"
    assert attr_defs[0]["data_type"] == "string"
    assert attr_defs[1]["identifier"] == "attr-002"
    assert attr_defs[1]["long_name"] == "Text"

    # Validate spec objects
    assert len(reqif_data["spec_objects"]) == 1
    spec_obj = reqif_data["spec_objects"][0]
    assert spec_obj["identifier"] == "req-001"
    assert spec_obj["spec_type_ref"] == "type-001"
    assert len(spec_obj["attributes"]) == 2

    # Validate attribute values
    attr_vals = spec_obj["attributes"]
    assert attr_vals[0]["definition_ref"] == "attr-001"
    assert attr_vals[0]["value"] == "REQ-001"
    assert attr_vals[1]["definition_ref"] == "attr-002"
    assert attr_vals[1]["value"] == "Test requirement text"


def test_reject_malformed_xml() -> None:
    """Test rejection of malformed XML with clear error message."""

    # Malformed XML: missing closing tag
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Test Baseline
  </REQ-IF-HEADER>
</REQ-IF>
"""

    # Parse the malformed XML
    result = parse_reqif_xml(malformed_xml)

    # Assert failure
    assert isinstance(result, Failure), "Expected Failure for malformed XML, got Success"

    error = result.failure()

    # Assert error message contains "Malformed XML"
    assert isinstance(error, ValueError)
    assert "Malformed XML" in str(error)


def test_reject_invalid_root_element() -> None:
    """Test rejection of XML with invalid root element."""

    # XML with wrong root element
    invalid_root_xml = """<?xml version="1.0" encoding="UTF-8"?>
<INVALID-ROOT>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Test Baseline</TITLE>
  </REQ-IF-HEADER>
</INVALID-ROOT>
"""

    # Parse the XML with invalid root
    result = parse_reqif_xml(invalid_root_xml)

    # Assert failure
    assert isinstance(result, Failure), "Expected Failure for invalid root element, got Success"

    error = result.failure()

    # Assert error message mentions invalid root
    assert isinstance(error, ValueError)
    assert "Invalid ReqIF root element" in str(error)
    assert "Expected REQ-IF" in str(error)


def test_reject_missing_header() -> None:
    """Test rejection of ReqIF XML missing required REQ-IF-HEADER."""

    # ReqIF XML missing header
    missing_header_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-CONTENT>
    <SPEC-OBJECTS>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the XML
    result = parse_reqif_xml(missing_header_xml)

    # Assert failure
    assert isinstance(result, Failure), "Expected Failure for missing header, got Success"

    error = result.failure()

    # Assert error message mentions missing header
    assert isinstance(error, ValueError)
    assert "REQ-IF-HEADER element not found" in str(error)


def test_reject_missing_content() -> None:
    """Test rejection of ReqIF XML missing required REQ-IF-CONTENT."""

    # ReqIF XML missing content
    missing_content_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Test Baseline</TITLE>
  </REQ-IF-HEADER>
</REQ-IF>
"""

    # Parse the XML
    result = parse_reqif_xml(missing_content_xml)

    # Assert failure
    assert isinstance(result, Failure), "Expected Failure for missing content, got Success"

    error = result.failure()

    # Assert error message mentions missing content
    assert isinstance(error, ValueError)
    assert "REQ-IF-CONTENT element not found" in str(error)


def test_handle_empty_reqif_no_spec_objects() -> None:
    """Test handling empty ReqIF (no SpecObjects) without error."""

    # ReqIF XML with no SpecObjects (valid but empty)
    empty_reqif_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Empty Baseline</TITLE>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES>
      <SPEC-OBJECT-TYPE IDENTIFIER="type-001" LONG-NAME="Requirement Type">
        <SPEC-ATTRIBUTES>
        </SPEC-ATTRIBUTES>
      </SPEC-OBJECT-TYPE>
    </SPEC-TYPES>
    <SPEC-OBJECTS>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the empty ReqIF
    result = parse_reqif_xml(empty_reqif_xml)

    # Assert successful parsing
    assert isinstance(result, Success), f"Expected Success for empty ReqIF, got Failure: {result}"

    reqif_data = result.unwrap()

    # Validate that it parsed successfully but has no SpecObjects
    assert reqif_data["header"]["identifier"] == "header-001"
    assert reqif_data["header"]["title"] == "Empty Baseline"
    assert len(reqif_data["spec_objects"]) == 0, "Expected zero SpecObjects in empty ReqIF"
    assert len(reqif_data["spec_types"]) == 1, "Expected SpecType to be present"


def test_handle_invalid_spec_type_reference() -> None:
    """Test handling invalid SpecType reference (missing SpecType)."""

    # ReqIF XML with SpecObject referencing non-existent SpecType
    invalid_ref_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Test Baseline</TITLE>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES>
      <SPEC-OBJECT-TYPE IDENTIFIER="type-001" LONG-NAME="Requirement Type">
        <SPEC-ATTRIBUTES>
        </SPEC-ATTRIBUTES>
      </SPEC-OBJECT-TYPE>
    </SPEC-TYPES>
    <SPEC-OBJECTS>
      <SPEC-OBJECT IDENTIFIER="req-001">
        <TYPE>
          <SPEC-OBJECT-TYPE-REF>type-999-NONEXISTENT</SPEC-OBJECT-TYPE-REF>
        </TYPE>
        <VALUES>
        </VALUES>
      </SPEC-OBJECT>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the ReqIF with invalid reference
    result = parse_reqif_xml(invalid_ref_xml)

    # Parser should succeed - it doesn't validate referential integrity
    # That's the job of the normalization/validation layer
    assert isinstance(result, Success), "Parser should succeed even with invalid references"

    reqif_data = result.unwrap()

    # Validate that the invalid reference is preserved in the data structure
    assert len(reqif_data["spec_objects"]) == 1
    spec_obj = reqif_data["spec_objects"][0]
    assert spec_obj["spec_type_ref"] == "type-999-NONEXISTENT"

    # Referential integrity validation happens in the normalization layer,
    # not in the parser layer


def test_parse_from_file_path() -> None:
    """Test parsing ReqIF from file path (using existing fixture)."""

    sample_reqif_file = FIXTURES_DIR / "sample_baseline.reqif"

    if not sample_reqif_file.exists():
        pytest.skip(f"Sample ReqIF fixture not found: {sample_reqif_file}")

    # Parse from file path
    result = parse_reqif_xml(sample_reqif_file)

    # Assert successful parsing
    assert isinstance(result, Success), f"Expected Success, got Failure: {result}"

    reqif_data = result.unwrap()

    # Validate basic structure
    assert "header" in reqif_data
    assert "spec_objects" in reqif_data
    assert "spec_types" in reqif_data
    assert "attribute_definitions" in reqif_data


def test_handle_missing_optional_fields() -> None:
    """Test handling ReqIF with missing optional fields."""

    # ReqIF XML with minimal required fields only (no COMMENT, etc.)
    minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Minimal Baseline</TITLE>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES>
    </SPEC-TYPES>
    <SPEC-OBJECTS>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the minimal ReqIF
    result = parse_reqif_xml(minimal_xml)

    # Assert successful parsing
    assert isinstance(result, Success), f"Expected Success for minimal ReqIF, got Failure: {result}"

    reqif_data = result.unwrap()

    # Validate that optional fields are handled gracefully
    assert reqif_data["header"]["identifier"] == "header-001"
    assert reqif_data["header"]["title"] == "Minimal Baseline"
    assert reqif_data["header"]["comment"] is None, "Expected comment to be None when absent"
    assert len(reqif_data["spec_objects"]) == 0
    assert len(reqif_data["spec_types"]) == 0


def test_handle_multiple_spec_objects() -> None:
    """Test parsing ReqIF with multiple SpecObjects."""

    # ReqIF XML with 3 SpecObjects
    multi_spec_obj_xml = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF>
  <REQ-IF-HEADER IDENTIFIER="header-001">
    <TITLE>Multi-Object Baseline</TITLE>
  </REQ-IF-HEADER>
  <REQ-IF-CONTENT>
    <SPEC-TYPES>
      <SPEC-OBJECT-TYPE IDENTIFIER="type-001" LONG-NAME="Requirement">
        <SPEC-ATTRIBUTES>
          <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="attr-key" LONG-NAME="Key"/>
        </SPEC-ATTRIBUTES>
      </SPEC-OBJECT-TYPE>
    </SPEC-TYPES>
    <SPEC-OBJECTS>
      <SPEC-OBJECT IDENTIFIER="req-001">
        <TYPE>
          <SPEC-OBJECT-TYPE-REF>type-001</SPEC-OBJECT-TYPE-REF>
        </TYPE>
        <VALUES>
          <ATTRIBUTE-VALUE-STRING>
            <DEFINITION>
              <ATTRIBUTE-DEFINITION-STRING-REF>attr-key</ATTRIBUTE-DEFINITION-STRING-REF>
            </DEFINITION>
            <THE-VALUE>REQ-001</THE-VALUE>
          </ATTRIBUTE-VALUE-STRING>
        </VALUES>
      </SPEC-OBJECT>
      <SPEC-OBJECT IDENTIFIER="req-002">
        <TYPE>
          <SPEC-OBJECT-TYPE-REF>type-001</SPEC-OBJECT-TYPE-REF>
        </TYPE>
        <VALUES>
          <ATTRIBUTE-VALUE-STRING>
            <DEFINITION>
              <ATTRIBUTE-DEFINITION-STRING-REF>attr-key</ATTRIBUTE-DEFINITION-STRING-REF>
            </DEFINITION>
            <THE-VALUE>REQ-002</THE-VALUE>
          </ATTRIBUTE-VALUE-STRING>
        </VALUES>
      </SPEC-OBJECT>
      <SPEC-OBJECT IDENTIFIER="req-003">
        <TYPE>
          <SPEC-OBJECT-TYPE-REF>type-001</SPEC-OBJECT-TYPE-REF>
        </TYPE>
        <VALUES>
          <ATTRIBUTE-VALUE-STRING>
            <DEFINITION>
              <ATTRIBUTE-DEFINITION-STRING-REF>attr-key</ATTRIBUTE-DEFINITION-STRING-REF>
            </DEFINITION>
            <THE-VALUE>REQ-003</THE-VALUE>
          </ATTRIBUTE-VALUE-STRING>
        </VALUES>
      </SPEC-OBJECT>
    </SPEC-OBJECTS>
  </REQ-IF-CONTENT>
</REQ-IF>
"""

    # Parse the ReqIF
    result = parse_reqif_xml(multi_spec_obj_xml)

    # Assert successful parsing
    assert isinstance(result, Success), f"Expected Success, got Failure: {result}"

    reqif_data = result.unwrap()

    # Validate that all 3 SpecObjects are parsed
    assert len(reqif_data["spec_objects"]) == 3
    assert reqif_data["spec_objects"][0]["identifier"] == "req-001"
    assert reqif_data["spec_objects"][1]["identifier"] == "req-002"
    assert reqif_data["spec_objects"][2]["identifier"] == "req-003"
