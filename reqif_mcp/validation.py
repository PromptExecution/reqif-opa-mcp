"""Requirement record validation module.

This module provides validation functions for requirement records against
the reqif-mcp/1 JSON schema.
"""

import json
from pathlib import Path
from typing import Any, TypedDict

from jsonschema import Draft202012Validator
from returns.result import Failure, Result, Success


class ValidationErrorDetail(TypedDict):
    """Single validation error detail."""

    field: str
    message: str
    value: Any


class ValidationResult(TypedDict):
    """Validation result structure."""

    valid: bool
    errors: list[ValidationErrorDetail]


def load_schema(schema_path: Path | str) -> Result[dict[str, Any], Exception]:
    """Load JSON schema from file.

    Args:
        schema_path: Path to JSON schema file

    Returns:
        Success with schema dict or Failure with exception
    """
    try:
        path = Path(schema_path)
        with path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        return Success(schema)
    except Exception as e:
        return Failure(e)


def validate_requirement_record(
    record: dict[str, Any],
    schema: dict[str, Any],
) -> Result[ValidationResult, Exception]:
    """Validate requirement record against JSON schema.

    Args:
        record: Requirement record object to validate
        schema: JSON schema to validate against

    Returns:
        Success with ValidationResult or Failure with exception
    """
    try:
        validator = Draft202012Validator(schema)
        errors: list[ValidationErrorDetail] = []

        # Collect all validation errors
        for error in validator.iter_errors(record):
            errors.append(
                {
                    "field": ".".join(str(p) for p in error.path) or "root",
                    "message": error.message,
                    "value": error.instance if hasattr(error, "instance") else None,
                }
            )

        result: ValidationResult = {
            "valid": len(errors) == 0,
            "errors": errors,
        }

        return Success(result)

    except Exception as e:
        return Failure(e)


def validate_requirement_record_from_schema_file(
    record: dict[str, Any],
    schema_path: Path | str,
) -> Result[ValidationResult, Exception]:
    """Validate requirement record against schema file.

    Convenience function that loads schema and validates in one call.

    Args:
        record: Requirement record object to validate
        schema_path: Path to JSON schema file

    Returns:
        Success with ValidationResult or Failure with exception
    """
    schema_result = load_schema(schema_path)
    match schema_result:
        case Success(schema):
            return validate_requirement_record(record, schema)
        case Failure(error):
            return Failure(error)
        case _:
            # This should never happen given Result type, but mypy needs it
            return Failure(Exception("Unexpected result type"))
