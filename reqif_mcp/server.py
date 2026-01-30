"""FastMCP 3.0 Server for ReqIF Compliance Gate System.

This module implements the MCP server that exposes ReqIF tools and resources
for compliance gate integration in CI/CD pipelines.

The server supports both HTTP and STDIO transports:
- HTTP: for multi-client CI usage
- STDIO: for local development and testing

Server State:
- Maintains in-memory storage of parsed ReqIF baselines indexed by handle
- Each handle maps to a list of requirement records

Tools:
- reqif.parse: Parse and store ReqIF XML
- reqif.validate: Validate requirement records
- reqif.query: Query requirements with filtering
- reqif.write_verification: Write verification events
- reqif.export_req_set: Export requirement subsets
"""

import base64
from typing import Any

from fastmcp import FastMCP
from returns.result import Failure, Result, Success
from ulid import ULID

from reqif_mcp.normalization import normalize_reqif
from reqif_mcp.reqif_parser import parse_reqif_xml
from reqif_mcp.validation import validate_requirement_integrity

# Initialize FastMCP server
mcp = FastMCP("reqif-mcp", version="0.1.0")

# In-memory storage for parsed ReqIF baselines
# Key: handle (str), Value: list of requirement records (list[dict[str, Any]])
_baseline_store: dict[str, list[dict[str, Any]]] = {}


def get_baseline_by_handle(handle: str) -> Result[list[dict[str, Any]], ValueError]:
    """Retrieve requirement records by handle from in-memory store.

    Args:
        handle: Unique identifier for the baseline

    Returns:
        Result containing list of requirement records or ValueError if not found
    """
    if handle not in _baseline_store:
        return Failure(ValueError(f"Baseline not found for handle: {handle}"))
    return Success(_baseline_store[handle])


def store_baseline(handle: str, requirements: list[dict[str, Any]]) -> None:
    """Store requirement records in in-memory store.

    Args:
        handle: Unique identifier for the baseline
        requirements: List of requirement records to store
    """
    _baseline_store[handle] = requirements


def clear_baseline_store() -> None:
    """Clear all baselines from in-memory store.

    Used primarily for testing and cleanup.
    """
    _baseline_store.clear()


@mcp.tool()
def reqif_parse(
    xml_b64: str,
    policy_baseline_id: str = "default",
    policy_baseline_version: str = "1.0.0",
) -> dict[str, Any]:
    """Parse ReqIF XML and store parsed requirement records.

    Args:
        xml_b64: Base64-encoded ReqIF 1.2 XML string
        policy_baseline_id: Policy baseline identifier (default: "default")
        policy_baseline_version: Policy baseline version (default: "1.0.0")

    Returns:
        Dictionary with handle field on success, or error field on failure
    """
    try:
        # Decode base64 XML
        xml_bytes = base64.b64decode(xml_b64)
        xml_string = xml_bytes.decode("utf-8")
    except Exception as e:
        return create_error_response(ValueError(f"Failed to decode base64 XML: {e}"))

    # Parse ReqIF XML
    parse_result = parse_reqif_xml(xml_string)
    if isinstance(parse_result, Failure):
        return create_error_response(parse_result.failure())

    reqif_data = parse_result.unwrap()

    # Normalize ReqIF data into requirement records
    normalize_result = normalize_reqif(reqif_data, policy_baseline_id, policy_baseline_version)
    if isinstance(normalize_result, Failure):
        return create_error_response(normalize_result.failure())

    requirements = normalize_result.unwrap()

    # Generate unique handle (ULID)
    handle = str(ULID())

    # Store parsed requirement records in memory
    store_baseline(handle, requirements)

    # Return handle
    return {
        "handle": handle,
        "requirement_count": len(requirements),
        "policy_baseline": {
            "id": policy_baseline_id,
            "version": policy_baseline_version,
        },
    }


@mcp.tool()
def reqif_validate(
    handle: str,
    mode: str = "basic",
) -> dict[str, Any]:
    """Validate parsed requirement records against integrity rules.

    Args:
        handle: Unique identifier for the baseline
        mode: Validation mode - "basic" (structure only) or "strict" (referential integrity)

    Returns:
        Dictionary with validation report on success, or error field on failure
    """
    # Validate mode parameter
    if mode not in ("basic", "strict"):
        return create_error_response(ValueError(f"Invalid mode '{mode}'. Must be 'basic' or 'strict'"))

    # Retrieve requirement records by handle
    baseline_result = get_baseline_by_handle(handle)
    if isinstance(baseline_result, Failure):
        return create_error_response(baseline_result.failure())

    requirements = baseline_result.unwrap()

    # Call validation function
    validation_result = validate_requirement_integrity(requirements, mode)
    if isinstance(validation_result, Failure):
        return create_error_response(validation_result.failure())

    # Return structured validation report
    report = validation_result.unwrap()
    return {
        "valid": report["valid"],
        "errors": report["errors"],
        "warnings": report["warnings"],
        "mode": mode,
        "requirement_count": len(requirements),
    }


@mcp.tool()
def reqif_query(
    handle: str,
    subtypes: list[str] | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Query requirements with filtering and pagination.

    Args:
        handle: Baseline identifier (handle from reqif.parse)
        subtypes: Filter by subtypes (AND logic - all must match). Optional.
        status: Filter by status (active/obsolete/draft). Optional.
        limit: Maximum number of results to return. Optional (no limit if None).
        offset: Number of results to skip (for pagination). Default: 0.

    Returns:
        Dictionary with requirements array on success, or error field on failure
    """
    # Retrieve requirement records by handle
    baseline_result = get_baseline_by_handle(handle)
    if isinstance(baseline_result, Failure):
        return create_error_response(baseline_result.failure())

    requirements = baseline_result.unwrap()

    # Apply filters
    filtered_requirements = requirements

    # Filter by subtypes (AND logic - all subtypes must be present)
    if subtypes:
        filtered_requirements = [
            req for req in filtered_requirements
            if all(subtype in req.get("subtypes", []) for subtype in subtypes)
        ]

    # Filter by status
    if status:
        # Validate status value
        if status not in ("active", "obsolete", "draft"):
            return create_error_response(ValueError(f"Invalid status '{status}'. Must be 'active', 'obsolete', or 'draft'"))
        filtered_requirements = [
            req for req in filtered_requirements
            if req.get("status") == status
        ]

    # Apply pagination
    start_idx = offset
    if limit is not None:
        end_idx = start_idx + limit
        paginated_requirements = filtered_requirements[start_idx:end_idx]
    else:
        paginated_requirements = filtered_requirements[start_idx:]

    return {
        "requirements": paginated_requirements,
        "total_count": len(filtered_requirements),
        "returned_count": len(paginated_requirements),
        "offset": offset,
    }


def create_error_response(error: Exception) -> dict[str, Any]:
    """Create standardized error response dictionary.

    Args:
        error: Exception that occurred

    Returns:
        Dictionary with error field containing message and type
    """
    return {
        "error": {
            "message": str(error),
            "type": type(error).__name__,
        }
    }


def run_server(transport: str = "stdio") -> None:
    """Start the FastMCP server with specified transport.

    Args:
        transport: Transport mode - 'stdio' for local dev, 'http' for CI/CD
    """
    if transport == "http":
        # HTTP transport for multi-client CI usage
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        # STDIO transport for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    # Default to STDIO transport for local development
    run_server(transport="stdio")
