"""Tests for the HTTP health endpoint."""

from __future__ import annotations

import asyncio
import json

from reqif_mcp.server import health_check


def test_health_check_reports_ready_server() -> None:
    """The custom health route should return a stable ready payload."""
    response = asyncio.run(health_check(None))
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["status"] == "ok"
    assert payload["server"] == "reqif-mcp"
    assert payload["transport"] == "http"
    assert payload["mcp"]["ready"] is True
