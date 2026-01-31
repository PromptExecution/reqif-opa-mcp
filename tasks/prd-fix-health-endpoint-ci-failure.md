# PRD: Fix CI Compliance Gate Health Check Failure

## Introduction

The CI pipeline compliance gate is failing because the FastMCP server lacks a `/health` endpoint for startup verification. The curl health check returns 404, causing the pipeline to fail even though the server starts successfully. This PRD addresses the root cause by upgrading to FastMCP 3.0 (which has native health endpoint support), implementing proper server startup verification, and improving CI robustness.

## Goals

- Upgrade FastMCP from 2.14.4 to 3.0 to leverage native health endpoint support
- Implement `/health` endpoint that returns server and MCP protocol readiness status
- Add proper startup logging and failure diagnostics to CI pipeline
- Ensure CI can reliably verify server readiness before running compliance tests
- Maintain backward compatibility with existing MCP tools and resources

## User Stories

### US-037: Upgrade FastMCP to version 3.0
**Description:** As a developer, I need to upgrade to FastMCP 3.0 so we can use native health endpoint support and improved HTTP transport features.

**Acceptance Criteria:**
- [ ] Update pyproject.toml to require `fastmcp >= 3.0.0`
- [ ] Run `uv sync` to update dependencies
- [ ] Review FastMCP 3.0 migration guide for breaking changes
- [ ] Update server initialization code for any API changes
- [ ] Verify existing MCP tools still work after upgrade
- [ ] Typecheck passes with new FastMCP version

### US-038: Implement health endpoint with MCP readiness check
**Description:** As a CI pipeline, I need a `/health` endpoint that confirms both HTTP server and MCP protocol readiness so I can verify successful startup.

**Acceptance Criteria:**
- [ ] Implement `/health` endpoint at root path (not under `/mcp`)
- [ ] Return 200 OK status when server is ready
- [ ] JSON response includes: `{"status": "ok", "server": "reqif-mcp", "version": "...", "mcp": {"ready": true, "tools_count": N, "resources_count": M}}`
- [ ] Return 503 Service Unavailable if MCP server not ready
- [ ] Endpoint accessible without authentication
- [ ] Typecheck passes

### US-039: Add server log capture to CI pipeline
**Description:** As a developer debugging CI failures, I need server logs captured to a file so I can diagnose startup issues.

**Acceptance Criteria:**
- [ ] Redirect server stdout/stderr to `mcp_server.log` in CI script
- [ ] Ensure log file created before server starts
- [ ] On health check failure, cat log contents to CI output
- [ ] Log includes startup sequence, bound address, and any errors
- [ ] CI artifact uploads `mcp_server.log` on failure

### US-040: Add startup timeout and retry logic
**Description:** As a CI pipeline, I need intelligent startup verification with timeout and retries so transient issues don't cause false failures.

**Acceptance Criteria:**
- [ ] Increase sleep from 5s to 10s for server startup
- [ ] Implement retry loop: attempt health check up to 5 times with 2s intervals
- [ ] Each retry logs attempt number and failure reason
- [ ] Fail fast if server process dies (check PID)
- [ ] Total timeout: 20 seconds maximum
- [ ] Exit with clear error message if all retries exhausted

### US-041: Update CI workflow to use new health endpoint
**Description:** As a CI pipeline, I need to use the correct health endpoint path and handle responses properly.

**Acceptance Criteria:**
- [ ] Update health check URL from `/health` to documented FastMCP 3.0 path
- [ ] Parse JSON response and verify `status: "ok"` and `mcp.ready: true`
- [ ] Log health check response body on success for diagnostics
- [ ] Distinguish between server not running vs server not ready
- [ ] Script continues to compliance tests only after successful health check

### US-042: Document FastMCP 3.0 health endpoint behavior
**Description:** As a future developer, I need documentation explaining the health endpoint implementation so I understand how server readiness works.

**Acceptance Criteria:**
- [ ] Add section to README.md explaining health endpoint
- [ ] Document JSON response schema with example
- [ ] Explain difference between server running vs MCP ready states
- [ ] Document CI startup verification process
- [ ] Include troubleshooting section for common startup issues

## Functional Requirements

- FR-1: FastMCP server MUST be upgraded to version 3.0 or later
- FR-2: Server MUST expose `/health` endpoint accessible via HTTP GET
- FR-3: Health endpoint MUST return JSON with `status`, `server`, `version`, and `mcp` fields
- FR-4: Health endpoint MUST return HTTP 200 when both HTTP server and MCP protocol are ready
- FR-5: Health endpoint MUST return HTTP 503 when MCP protocol not ready
- FR-6: CI script MUST redirect server output to `mcp_server.log`
- FR-7: CI script MUST implement retry loop with 5 attempts at 2-second intervals
- FR-8: CI script MUST check PID liveness between health check attempts
- FR-9: CI script MUST output log contents on health check failure
- FR-10: Health check MUST complete within 20 seconds total timeout
- FR-11: CI MUST upload `mcp_server.log` as artifact on pipeline failure

## Non-Goals (Out of Scope)

- No custom health metrics beyond basic readiness (no memory/CPU monitoring)
- No authentication/authorization for health endpoint
- No integration with external monitoring systems (Prometheus, DataDog, etc.)
- No changes to OPA evaluation or SARIF reporting logic
- No health checks for downstream dependencies (OPA bundles, evidence store)

## Design Considerations

### Health Endpoint Response Schema
```json
{
  "status": "ok",
  "server": "reqif-mcp",
  "version": "0.1.0",
  "transport": "http",
  "mcp": {
    "ready": true,
    "protocol_version": "2024-11-05",
    "tools_count": 6,
    "resources_count": 2
  }
}
```

### CI Startup Verification Flow
```bash
# 1. Start server with logging
uv run python -m reqif_mcp --http --host 127.0.0.1 --port 8000 > mcp_server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > mcp_server.pid

# 2. Retry loop with timeout
for i in {1..5}; do
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "Server process died"
    cat mcp_server.log
    exit 1
  fi

  if curl -f -s http://127.0.0.1:8000/health | jq -e '.status == "ok" and .mcp.ready == true'; then
    echo "Server ready!"
    exit 0
  fi

  echo "Attempt $i failed, retrying..."
  sleep 2
done

echo "Health check timeout"
cat mcp_server.log
exit 1
```

## Technical Considerations

### FastMCP 3.0 Migration
- Review breaking changes in FastMCP 3.0 release notes
- Check for API changes in `@mcp.tool()` and `@mcp.resource()` decorators
- Verify HTTP transport initialization still uses `--http` flag
- Test that existing tools (`reqif.parse`, `reqif.validate`, etc.) still work

### Server Initialization Sequence
1. FastAPI app created
2. MCP server initialized
3. HTTP transport bound to port
4. Tools and resources registered
5. `/health` endpoint becomes available
6. MCP protocol ready (can accept tool calls)

### Error Scenarios
- **Server fails to bind port**: Health check times out, log shows bind error
- **MCP not ready**: Health returns 503, `mcp.ready: false`
- **Dependency missing**: Server crashes, PID check fails
- **Network issue**: Curl fails, retry logic engages

## Success Metrics

- CI pipeline startup verification completes in under 15 seconds on average
- Zero false failures due to health check timeout (after implementation)
- Server startup issues diagnosed within 30 seconds via log output
- Health endpoint responds in under 100ms when ready

## Open Questions

- Does FastMCP 3.0 provide native `/health` endpoint or do we need to implement custom route?
- Should health endpoint include ReqIF data source status (e.g., file accessibility)?
- Should we add liveness vs readiness probe distinction for Kubernetes deployment?
- What's the appropriate log rotation strategy for `mcp_server.log` in production?

## Implementation Notes

### FastMCP 3.0 Documentation Check
Before implementation, consult FastMCP 3.0 documentation to determine:
1. Native health endpoint path and response format
2. Migration guide for 2.x → 3.0 upgrade
3. Changes to HTTP transport initialization
4. Whether custom health endpoint implementation needed

### Testing Strategy
- **Local**: Start server, verify health endpoint returns expected JSON
- **Local**: Kill server mid-startup, verify CI script detects PID failure
- **Local**: Simulate slow startup, verify retry logic succeeds
- **CI**: Run updated pipeline, verify successful health check
- **CI**: Introduce failure (bad port), verify log capture works

## References

- FastMCP Documentation: https://github.com/jlowin/fastmcp
- CLAUDE.md: Package management section (ALWAYS use uv)
- Existing CI workflow: `.github/workflows/compliance-gate.yml`
- Server implementation: `reqif_mcp/server.py`
