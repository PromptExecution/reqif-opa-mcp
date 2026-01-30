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

from typing import Any

from fastmcp import FastMCP
from returns.result import Failure, Result, Success

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


# Placeholder for tools to be implemented in future user stories
# Tools will be registered here as @mcp.tool() decorators
# Example:
# @mcp.tool()
# def reqif_parse(xml_b64: str) -> dict[str, Any]:
#     """Parse ReqIF XML and return handle."""
#     pass


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
