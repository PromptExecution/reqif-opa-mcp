"""SARIF validator module for conformance checking against SARIF v2.1.0 schema."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from returns.result import Failure, Result, Success


class SARIFValidationErrorDetail:
    """Detailed information about a SARIF validation error."""

    def __init__(self, path: str, message: str, value: Any = None) -> None:
        self.path = path
        self.message = message
        self.value = value

    def __repr__(self) -> str:
        if self.value is not None:
            return f"SARIFValidationErrorDetail(path={self.path!r}, message={self.message!r}, value={self.value!r})"
        return f"SARIFValidationErrorDetail(path={self.path!r}, message={self.message!r})"


class SARIFValidationResult:
    """Result of SARIF validation."""

    def __init__(self, valid: bool, errors: list[SARIFValidationErrorDetail]) -> None:
        self.valid = valid
        self.errors = errors

    def __repr__(self) -> str:
        return f"SARIFValidationResult(valid={self.valid}, errors={self.errors!r})"


def load_sarif_schema(
    schema_path: str | Path | None = None,
) -> Result[dict[str, Any], Exception]:
    """Load SARIF v2.1.0 JSON schema from file.

    Args:
        schema_path: Optional path to SARIF schema file. If None, uses bundled schema.

    Returns:
        Success[dict]: Loaded schema object
        Failure[Exception]: If schema cannot be loaded
    """
    try:
        if schema_path is None:
            # Use bundled SARIF 2.1.0 schema
            default_schema_path = (
                Path(__file__).parent.parent / "schemas" / "sarif-schema-2.1.0.json"
            )
            schema_path = default_schema_path

        schema_path_obj = Path(schema_path)
        if not schema_path_obj.exists():
            return Failure(FileNotFoundError(f"Schema file not found: {schema_path}"))

        with schema_path_obj.open("r", encoding="utf-8") as f:
            schema = json.load(f)

        return Success(schema)
    except Exception as e:
        return Failure(e)


def validate_sarif(
    sarif_object: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> Result[SARIFValidationResult, Exception]:
    """Validate SARIF object against SARIF v2.1.0 JSON schema.

    Args:
        sarif_object: SARIF object to validate
        schema: Optional schema dict. If None, loads bundled schema.

    Returns:
        Success[SARIFValidationResult]: Validation result with errors array
        Failure[Exception]: If validation process fails (not schema violations)
    """
    try:
        # Load schema if not provided
        if schema is None:
            schema_result = load_sarif_schema()
            if isinstance(schema_result, Failure):
                return Failure(schema_result.failure())
            schema = schema_result.unwrap()

        # Create validator
        validator = Draft7Validator(schema)

        # Collect validation errors
        errors: list[SARIFValidationErrorDetail] = []
        for error in validator.iter_errors(sarif_object):
            # Build JSON path string
            path_parts = list(error.absolute_path)
            if path_parts:
                json_path = "$." + ".".join(str(p) for p in path_parts)
            else:
                json_path = "$"

            # Create error detail
            error_detail = SARIFValidationErrorDetail(
                path=json_path,
                message=error.message,
                value=error.instance if error.instance is not None else None,
            )
            errors.append(error_detail)

        # Create validation result
        is_valid = len(errors) == 0
        result = SARIFValidationResult(valid=is_valid, errors=errors)

        return Success(result)
    except Exception as e:
        return Failure(e)


def validate_sarif_from_schema_file(
    sarif_object: dict[str, Any],
    schema_path: str | Path,
) -> Result[SARIFValidationResult, Exception]:
    """Validate SARIF object against schema from file path (convenience function).

    Args:
        sarif_object: SARIF object to validate
        schema_path: Path to SARIF schema file

    Returns:
        Success[SARIFValidationResult]: Validation result with errors array
        Failure[Exception]: If validation process fails
    """
    try:
        # Load schema
        schema_result = load_sarif_schema(schema_path)
        if isinstance(schema_result, Failure):
            return Failure(schema_result.failure())
        schema = schema_result.unwrap()

        # Validate
        return validate_sarif(sarif_object, schema)
    except Exception as e:
        return Failure(e)


def validate_sarif_file(
    sarif_file_path: str | Path,
    schema: dict[str, Any] | None = None,
) -> Result[SARIFValidationResult, Exception]:
    """Validate SARIF file against SARIF v2.1.0 JSON schema.

    Args:
        sarif_file_path: Path to SARIF file to validate
        schema: Optional schema dict. If None, loads bundled schema.

    Returns:
        Success[SARIFValidationResult]: Validation result with errors array
        Failure[Exception]: If validation process fails
    """
    try:
        # Load SARIF file
        sarif_path = Path(sarif_file_path)
        if not sarif_path.exists():
            return Failure(FileNotFoundError(f"SARIF file not found: {sarif_file_path}"))

        with sarif_path.open("r", encoding="utf-8") as f:
            sarif_object = json.load(f)

        # Validate
        return validate_sarif(sarif_object, schema)
    except Exception as e:
        return Failure(e)
