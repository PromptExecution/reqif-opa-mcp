"""
ReqIF Normalization Module

Normalizes ReqIF data into canonical requirement records conforming to reqif-mcp/1 schema.
"""

import uuid
from typing import Any

from returns.result import Failure, Result, Success

from reqif_mcp.reqif_parser import AttributeDefinition, ReqIFData, SpecObject, SpecType


def normalize_reqif(
    reqif_data: ReqIFData, policy_baseline_id: str = "default", policy_baseline_version: str = "1.0.0"
) -> Result[list[dict[str, Any]], Exception]:
    """
    Normalize ReqIF data into requirement records.

    Args:
        reqif_data: Parsed ReqIF data structure
        policy_baseline_id: Policy baseline identifier (default: "default")
        policy_baseline_version: Policy baseline version (default: "1.0.0")

    Returns:
        Result containing list of requirement records or Exception
    """
    try:
        requirement_records: list[dict[str, Any]] = []

        # Build lookup maps for SpecTypes and AttributeDefinitions
        spec_types_map = {st["identifier"]: st for st in reqif_data["spec_types"]}
        attr_defs_map = {ad["identifier"]: ad for ad in reqif_data["attribute_definitions"]}

        for spec_obj in reqif_data["spec_objects"]:
            record_result = _normalize_spec_object(
                spec_obj,
                spec_types_map,
                attr_defs_map,
                policy_baseline_id,
                policy_baseline_version,
            )

            if isinstance(record_result, Failure):
                return record_result

            requirement_records.append(record_result.unwrap())

        return Success(requirement_records)

    except Exception as e:
        return Failure(e)


def _normalize_spec_object(
    spec_obj: SpecObject,
    spec_types_map: dict[str, SpecType],
    attr_defs_map: dict[str, AttributeDefinition],
    policy_baseline_id: str,
    policy_baseline_version: str,
) -> Result[dict[str, Any], Exception]:
    """
    Normalize a single SpecObject to a requirement record.

    Args:
        spec_obj: ReqIF SpecObject to normalize
        spec_types_map: Lookup map of SpecTypes by identifier
        attr_defs_map: Lookup map of AttributeDefinitions by identifier
        policy_baseline_id: Policy baseline identifier
        policy_baseline_version: Policy baseline version

    Returns:
        Result containing normalized requirement record or Exception
    """
    try:
        # Extract uid from ReqIF identifier or generate deterministic UID
        uid = _extract_or_generate_uid(spec_obj["identifier"])

        # Build attributes map from ReqIF attributes
        attrs_map: dict[str, Any] = {}
        for attr_value in spec_obj["attributes"]:
            def_ref = attr_value.get("definition_ref", "")
            if def_ref in attr_defs_map:
                attr_def = attr_defs_map[def_ref]
                long_name = attr_def["long_name"].lower().replace(" ", "_").replace("-", "_")
                attrs_map[long_name] = attr_value.get("value", "")

        # Extract key (use identifier if Key attribute not found)
        key = attrs_map.get("key", spec_obj["identifier"])

        # Extract text (use Description or Text attribute)
        text = attrs_map.get("text", attrs_map.get("description", ""))

        # Extract subtypes (use Type attribute or infer from SpecType)
        subtypes = _extract_subtypes(spec_obj, spec_types_map, attrs_map)

        # Extract status (default to "active")
        status = attrs_map.get("status", "active")
        if status not in ["active", "obsolete", "draft"]:
            status = "active"

        # Build policy_baseline (default values with computed hash)
        policy_baseline = {
            "id": policy_baseline_id,
            "version": policy_baseline_version,
            "hash": _compute_baseline_hash(policy_baseline_id, policy_baseline_version),
        }

        # Build rubrics (default OPA rubric)
        rubrics = _build_default_rubrics(subtypes)

        # Build attrs object (additional attributes)
        attrs: dict[str, Any] = {}
        if "severity" in attrs_map:
            attrs["severity"] = attrs_map["severity"]
        if "owner" in attrs_map:
            attrs["owner"] = attrs_map["owner"]
        if "verify_method" in attrs_map:
            attrs["verify_method"] = attrs_map["verify_method"]

        # Build requirement record
        requirement_record: dict[str, Any] = {
            "uid": uid,
            "key": key,
            "subtypes": subtypes,
            "status": status,
            "policy_baseline": policy_baseline,
            "rubrics": rubrics,
            "text": text,
        }

        # Only include attrs if non-empty
        if attrs:
            requirement_record["attrs"] = attrs

        return Success(requirement_record)

    except Exception as e:
        return Failure(e)


def _extract_or_generate_uid(identifier: str) -> str:
    """
    Extract UID from ReqIF identifier or generate deterministic UID.

    For deterministic normalization, when the identifier is not alphanumeric,
    generates a stable UUID v5 from the identifier using a custom namespace.
    This ensures the same ReqIF identifier always produces the same UID.

    Args:
        identifier: ReqIF identifier

    Returns:
        UID string (stable identifier or deterministic UUID v5)
    """
    # If identifier looks like a valid UID (alphanumeric with hyphens/underscores), use it
    if identifier and all(c.isalnum() or c in "_-" for c in identifier):
        return identifier

    # Generate deterministic UUID v5 from identifier
    # Using a custom namespace for ReqIF identifiers to ensure uniqueness
    # This ensures the same identifier always produces the same UID
    reqif_namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # Custom namespace for ReqIF
    deterministic_uuid = uuid.uuid5(reqif_namespace, identifier)
    return str(deterministic_uuid)


def _extract_subtypes(
    spec_obj: SpecObject,
    spec_types_map: dict[str, SpecType],
    attrs_map: dict[str, Any],
) -> list[str]:
    """
    Extract subtypes from SpecObject attributes or SpecType.

    Args:
        spec_obj: SpecObject being normalized
        spec_types_map: Lookup map of SpecTypes
        attrs_map: Extracted attributes map

    Returns:
        List of subtype strings (uppercase with underscores)
    """
    # Check for explicit subtypes attribute
    if "subtypes" in attrs_map:
        subtypes_value = attrs_map["subtypes"]
        if isinstance(subtypes_value, str):
            # Split by comma and normalize
            subtypes = [
                s.strip().upper().replace(" ", "_").replace("-", "_")
                for s in subtypes_value.split(",")
            ]
            return [s for s in subtypes if s]

    # Check for type attribute
    if "type" in attrs_map:
        type_value = attrs_map["type"]
        if isinstance(type_value, str):
            normalized = type_value.upper().replace(" ", "_").replace("-", "_")
            return [normalized]

    # Infer from SpecType long_name
    spec_type_ref = spec_obj.get("spec_type_ref", "")
    if spec_type_ref in spec_types_map:
        spec_type = spec_types_map[spec_type_ref]
        long_name = spec_type["long_name"]
        normalized = long_name.upper().replace(" ", "_").replace("-", "_")
        return [normalized]

    # Default to GENERAL if no type information found
    return ["GENERAL"]


def _compute_baseline_hash(baseline_id: str, baseline_version: str) -> str:
    """
    Compute a simple hash for policy baseline.

    In a real implementation, this would compute a cryptographic hash
    of the baseline content. For MVP, we use a placeholder.

    Args:
        baseline_id: Baseline identifier
        baseline_version: Baseline version

    Returns:
        Hash string (placeholder for MVP)
    """
    import hashlib

    content = f"{baseline_id}:{baseline_version}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _build_default_rubrics(subtypes: list[str]) -> list[dict[str, str]]:
    """
    Build default OPA rubrics based on subtypes.

    Args:
        subtypes: List of requirement subtypes

    Returns:
        List of rubric objects with OPA configuration
    """
    rubrics: list[dict[str, str]] = []

    # Create a rubric for each subtype
    for subtype in subtypes:
        package_name = subtype.lower().replace("_", ".")
        rubrics.append(
            {
                "engine": "opa",
                "bundle": "org/compliance",
                "package": f"compliance.{package_name}",
                "rule": "decision",
            }
        )

    return rubrics
