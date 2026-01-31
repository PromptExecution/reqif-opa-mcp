#!/bin/bash
# Ralph Wiggum - Local runner for reqif-opa-mcp
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec uv run --script ralph/ralphython.py "$@"
