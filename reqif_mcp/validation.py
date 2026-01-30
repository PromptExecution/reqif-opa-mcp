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


class IntegrityErrorDetail(TypedDict):
    """Integrity validation error or warning detail."""

    severity: str  # "error" or "warning"
    field: str
    message: str
    record_uid: str | None


class IntegrityValidationResult(TypedDict):
    """Integrity validation result structure."""

    valid: bool
    errors: list[IntegrityErrorDetail]
    warnings: list[IntegrityErrorDetail]


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


def validate_requirement_integrity(
    requirements: list[dict[str, Any]],
    mode: str = "basic",
) -> Result[IntegrityValidationResult, Exception]:
    """Validate integrity of requirement records within a baseline.

    Performs integrity checks on a collection of requirement records:
    - UID uniqueness within the baseline
    - Policy baseline reference structure (id, version, hash present)
    - Rubric reference structure (engine, bundle, package, rule present)

    Args:
        requirements: List of requirement record objects
        mode: Validation mode - "basic" (structure only) or "strict" (referential integrity)

    Returns:
        Success with IntegrityValidationResult or Failure with exception
    """
    try:
        errors: list[IntegrityErrorDetail] = []
        warnings: list[IntegrityErrorDetail] = []

        # Check UID uniqueness
        uid_map: dict[str, int] = {}
        for idx, req in enumerate(requirements):
            uid = req.get("uid")
            if uid is None:
                errors.append(
                    {
                        "severity": "error",
                        "field": "uid",
                        "message": f"Missing uid in requirement at index {idx}",
                        "record_uid": None,
                    }
                )
                continue

            if uid in uid_map:
                errors.append(
                    {
                        "severity": "error",
                        "field": "uid",
                        "message": f"Duplicate uid '{uid}' found at indices {uid_map[uid]} and {idx}",
                        "record_uid": uid,
                    }
                )
            else:
                uid_map[uid] = idx

        # Validate each requirement record
        for req in requirements:
            uid = req.get("uid", "unknown")

            # Validate policy_baseline structure
            policy_baseline = req.get("policy_baseline")
            if policy_baseline is None:
                errors.append(
                    {
                        "severity": "error",
                        "field": "policy_baseline",
                        "message": "Missing policy_baseline",
                        "record_uid": uid,
                    }
                )
            elif not isinstance(policy_baseline, dict):
                errors.append(
                    {
                        "severity": "error",
                        "field": "policy_baseline",
                        "message": "policy_baseline must be an object",
                        "record_uid": uid,
                    }
                )
            else:
                # Check required fields in policy_baseline
                required_pb_fields = ["id", "version", "hash"]
                for field in required_pb_fields:
                    if field not in policy_baseline:
                        errors.append(
                            {
                                "severity": "error",
                                "field": f"policy_baseline.{field}",
                                "message": f"Missing required field '{field}' in policy_baseline",
                                "record_uid": uid,
                            }
                        )
                    elif not isinstance(policy_baseline[field], str):
                        errors.append(
                            {
                                "severity": "error",
                                "field": f"policy_baseline.{field}",
                                "message": f"Field '{field}' must be a string",
                                "record_uid": uid,
                            }
                        )
                    elif policy_baseline[field] == "":
                        errors.append(
                            {
                                "severity": "error",
                                "field": f"policy_baseline.{field}",
                                "message": f"Empty value for required field '{field}'",
                                "record_uid": uid,
                            }
                        )

            # Validate rubrics structure
            rubrics = req.get("rubrics")
            if rubrics is None:
                errors.append(
                    {
                        "severity": "error",
                        "field": "rubrics",
                        "message": "Missing rubrics array",
                        "record_uid": uid,
                    }
                )
            elif not isinstance(rubrics, list):
                errors.append(
                    {
                        "severity": "error",
                        "field": "rubrics",
                        "message": "rubrics must be an array",
                        "record_uid": uid,
                    }
                )
            else:
                # Check each rubric has required fields
                required_rubric_fields = ["engine", "bundle", "package", "rule"]
                for idx, rubric in enumerate(rubrics):
                    if not isinstance(rubric, dict):
                        errors.append(
                            {
                                "severity": "error",
                                "field": f"rubrics[{idx}]",
                                "message": f"Rubric at index {idx} must be an object",
                                "record_uid": uid,
                            }
                        )
                        continue

                    for field in required_rubric_fields:
                        if field not in rubric:
                            errors.append(
                                {
                                    "severity": "error",
                                    "field": f"rubrics[{idx}].{field}",
                                    "message": f"Missing required field '{field}' in rubric at index {idx}",
                                    "record_uid": uid,
                                }
                            )
                        elif not isinstance(rubric[field], str):
                            errors.append(
                                {
                                    "severity": "error",
                                    "field": f"rubrics[{idx}].{field}",
                                    "message": f"Field '{field}' must be a string",
                                    "record_uid": uid,
                                }
                            )
                        elif rubric[field] == "":
                            errors.append(
                                {
                                    "severity": "error",
                                    "field": f"rubrics[{idx}].{field}",
                                    "message": f"Empty value for required field '{field}'",
                                    "record_uid": uid,
                                }
                            )

        # In strict mode, add additional checks
        if mode == "strict":
            # Check that all requirements share same policy_baseline
            baselines = {
                req.get("policy_baseline", {}).get("id")
                for req in requirements
                if req.get("policy_baseline") is not None
            }
            if len(baselines) > 1:
                warnings.append(
                    {
                        "severity": "warning",
                        "field": "policy_baseline.id",
                        "message": f"Multiple policy baselines found in requirement set: {baselines}",
                        "record_uid": None,
                    }
                )

        result: IntegrityValidationResult = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

        return Success(result)

    except Exception as e:
        return Failure(e)


def validate_verification_event(
    event: dict[str, Any],
    schema: dict[str, Any],
) -> Result[ValidationResult, Exception]:
    """Validate verification event against JSON schema.

    Args:
        event: Verification event object to validate
        schema: JSON schema to validate against

    Returns:
        Success with ValidationResult or Failure with exception
    """
    try:
        validator = Draft202012Validator(schema)
        errors: list[ValidationErrorDetail] = []

        # Collect all validation errors
        for error in validator.iter_errors(event):
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


def validate_verification_event_from_schema_file(
    event: dict[str, Any],
    schema_path: Path | str,
) -> Result[ValidationResult, Exception]:
    """Validate verification event against JSON schema from file.

    Convenience function that loads schema and validates in one call.

    Args:
        event: Verification event object to validate
        schema_path: Path to JSON schema file

    Returns:
        Success with ValidationResult or Failure with exception
    """
    schema_result = load_schema(schema_path)
    match schema_result:
        case Success(schema):
            return validate_verification_event(event, schema)
        case Failure(error):
            return Failure(error)
        case _:
            # This should never happen given Result type, but mypy needs it
            return Failure(Exception("Unexpected result type"))
