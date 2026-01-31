"""Tests for requirement record validation module."""

from pathlib import Path

import pytest
from returns.result import Failure, Success

from reqif_mcp.validation import (
    validate_requirement_integrity,
    validate_requirement_record_from_schema_file,
)


class TestValidateRequirementIntegrity:
    """Tests for validate_requirement_integrity function."""

    def test_empty_string_in_rubric_field_fails(self):
        """Empty string values in rubric fields should fail validation."""
        req = {
            "uid": "test-1",
            "key": "TEST-1",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "",  # Empty string
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is False
        assert len(val_result["errors"]) == 1
        assert val_result["errors"][0]["field"] == "rubrics[0].engine"
        assert "Empty value" in val_result["errors"][0]["message"]

    def test_whitespace_only_string_in_rubric_field_fails(self):
        """Whitespace-only string values in rubric fields should fail validation."""
        req = {
            "uid": "test-2",
            "key": "TEST-2",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "   ",  # Whitespace-only
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is False
        assert len(val_result["errors"]) == 1
        assert val_result["errors"][0]["field"] == "rubrics[0].engine"
        assert "Empty value" in val_result["errors"][0]["message"]

    def test_valid_rubric_fields_pass(self):
        """Valid non-empty string values in rubric fields should pass validation."""
        req = {
            "uid": "test-3",
            "key": "TEST-3",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "opa",
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is True
        assert len(val_result["errors"]) == 0

    def test_integer_zero_in_rubric_field_does_not_trigger_empty_error(self):
        """Integer 0 in rubric field should not trigger empty value error.

        Although this violates the schema (which requires strings), the empty
        value validation should only apply to strings to avoid false positives.
        """
        req = {
            "uid": "test-4",
            "key": "TEST-4",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": 0,  # Integer 0
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        # Should pass integrity validation (type validation is separate)
        assert val_result["valid"] is True
        assert len(val_result["errors"]) == 0

    def test_boolean_false_in_rubric_field_does_not_trigger_empty_error(self):
        """Boolean False in rubric field should not trigger empty value error.

        Although this violates the schema (which requires strings), the empty
        value validation should only apply to strings to avoid false positives.
        """
        req = {
            "uid": "test-5",
            "key": "TEST-5",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": False,  # Boolean False
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        # Should pass integrity validation (type validation is separate)
        assert val_result["valid"] is True
        assert len(val_result["errors"]) == 0

    def test_empty_string_in_policy_baseline_field_fails(self):
        """Empty string values in policy_baseline fields should fail validation."""
        req = {
            "uid": "test-6",
            "key": "TEST-6",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "",  # Empty string
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "opa",
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is False
        assert len(val_result["errors"]) == 1
        assert val_result["errors"][0]["field"] == "policy_baseline.id"
        assert "Empty value" in val_result["errors"][0]["message"]

    def test_non_dict_requirement_returns_failure(self):
        """Non-dict requirements should return Failure rather than Success."""
        result = validate_requirement_integrity(["not-a-dict"])
        assert isinstance(result, Failure)


def test_missing_schema_file_returns_failure(tmp_path: Path) -> None:
    """Missing schema file should return Failure."""
    missing_schema = tmp_path / "missing.schema.json"
    result = validate_requirement_record_from_schema_file({}, missing_schema)
    assert isinstance(result, Failure)

    def test_whitespace_only_string_in_policy_baseline_field_fails(self):
        """Whitespace-only string values in policy_baseline fields should fail validation."""
        req = {
            "uid": "test-7",
            "key": "TEST-7",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "POL-2026.01",
                "version": "   ",  # Whitespace-only
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "opa",
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is False
        assert len(val_result["errors"]) == 1
        assert val_result["errors"][0]["field"] == "policy_baseline.version"
        assert "Empty value" in val_result["errors"][0]["message"]

    def test_integer_zero_in_policy_baseline_field_does_not_trigger_empty_error(self):
        """Integer 0 in policy_baseline field should not trigger empty value error."""
        req = {
            "uid": "test-8",
            "key": "TEST-8",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": 0,  # Integer 0
                "version": "2026.01",
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "opa",
                    "bundle": "org/test",
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        # Should pass integrity validation (type validation is separate)
        assert val_result["valid"] is True
        assert len(val_result["errors"]) == 0

    def test_multiple_empty_fields_all_reported(self):
        """All empty fields should be reported as errors."""
        req = {
            "uid": "test-9",
            "key": "TEST-9",
            "subtypes": ["TEST"],
            "status": "active",
            "text": "Test requirement",
            "policy_baseline": {
                "id": "",  # Empty
                "version": "",  # Empty
                "hash": "abc123",
            },
            "rubrics": [
                {
                    "engine": "",  # Empty
                    "bundle": "",  # Empty
                    "package": "test.pkg",
                    "rule": "decision",
                }
            ],
        }

        result = validate_requirement_integrity([req])
        assert isinstance(result, Success)
        val_result = result.unwrap()
        assert val_result["valid"] is False
        assert len(val_result["errors"]) == 4  # 2 policy_baseline + 2 rubric errors
        error_fields = {err["field"] for err in val_result["errors"]}
        assert "policy_baseline.id" in error_fields
        assert "policy_baseline.version" in error_fields
        assert "rubrics[0].engine" in error_fields
        assert "rubrics[0].bundle" in error_fields
