"""Command-line entry point for ReqIF MCP Server.

This module provides the CLI for starting the FastMCP server with different
transport modes (HTTP or STDIO).

Usage:
    python -m reqif_mcp              # Start with STDIO (default)
    python -m reqif_mcp --http       # Start with HTTP transport
    python -m reqif_mcp --help       # Show help
"""

import argparse
import sys

from reqif_mcp.server import run_server


def main() -> None:
    """Parse command-line arguments and start the server."""
    parser = argparse.ArgumentParser(
        description="ReqIF MCP Server - Compliance Gate System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m reqif_mcp              Start with STDIO transport (local dev)
  python -m reqif_mcp --http       Start with HTTP transport (CI/CD)
        """,
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP transport on 0.0.0.0:8000 (default: STDIO)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )

    args = parser.parse_args()

    transport = "http" if args.http else "stdio"

    try:
        print(f"Starting ReqIF MCP Server with {transport.upper()} transport...", file=sys.stderr)
        if transport == "http":
            print(f"Listening on {args.host}:{args.port}", file=sys.stderr)

        run_server(transport=transport)
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
