# Deployment Guide

This guide covers deploying the ReqIF-OPA-SARIF compliance gate system for local development, CI/CD integration, and containerized environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Running the FastMCP Server](#running-the-fastmcp-server)
4. [CI/CD Integration](#cicd-integration)
5. [Containerized Deployment](#containerized-deployment)
6. [Configuration Options](#configuration-options)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Dependencies

- **Python 3.10+**: The project requires Python 3.10 or higher
- **uv**: Package manager for Python dependencies (`pip install uv` or use official installer)
- **OPA**: Open Policy Agent binary for policy evaluation
  - Download from: https://www.openpolicyagent.org/docs/latest/#1-download-opa
  - Or install via package manager: `brew install opa` (macOS), `apt install opa` (Debian/Ubuntu)
- **Git**: For repository management and CI/CD integration

### Optional Dependencies

- **Docker**: For containerized deployment
- **pytest**: For running tests (installed as dev dependency)
- **mypy**: For type checking (installed as dev dependency)
- **ruff**: For linting (installed as dev dependency)

### System Requirements

- **Memory**: Minimum 512MB RAM (1GB+ recommended for production)
- **Disk**: Minimum 100MB for application and dependencies
- **CPU**: 1 core minimum (2+ cores recommended for concurrent evaluations)

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/reqif-opa-mcp.git
cd reqif-opa-mcp
```

### 2. Install Python 3.10+

Check your Python version:

```bash
python --version
```

If you need Python 3.10+, install it using:
- **macOS**: `brew install python@3.10`
- **Ubuntu/Debian**: `apt install python3.10`
- **Windows**: Download from https://www.python.org/downloads/

### 3. Install uv Package Manager

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip
pip install uv
```

### 4. Install Project Dependencies

```bash
# Install production dependencies
uv sync

# Install development dependencies (for testing and linting)
uv sync --all-extras
```

This will create a virtual environment in `.venv/` and install all dependencies specified in `pyproject.toml`.

### 5. Install OPA Binary

```bash
# macOS
brew install opa

# Linux (download latest release)
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
sudo mv opa /usr/local/bin/

# Verify installation
opa version
```

### 6. Initialize Evidence Store

```bash
# Create evidence store directories
mkdir -p evidence_store/{events,sarif,decision_logs}
```

### 7. Verify Installation

```bash
# Run type checking
uv run mypy --strict reqif_mcp/

# Run linting
uv run ruff check

# Run tests
uv run pytest
```

---

## Running the FastMCP Server

The FastMCP server can be run with either STDIO (for local development) or HTTP (for CI/CD integration) transport.

### STDIO Transport (Local Development)

For interactive development with MCP clients:

```bash
python -m reqif_mcp
```

This starts the server in STDIO mode, suitable for:
- Claude Desktop integration
- Interactive testing with MCP clients
- Local debugging

### HTTP Transport (CI/CD)

For production and CI/CD pipelines:

```bash
# Default (localhost:8000)
python -m reqif_mcp --http

# Custom host and port
python -m reqif_mcp --http --host 0.0.0.0 --port 8080
```

This starts the server with HTTP transport, suitable for:
- CI/CD pipeline integration
- Multi-client access
- Container deployments
- Remote access

### Server Options

```bash
# Show all options
python -m reqif_mcp --help

# Available options:
#   --http              Use HTTP transport (default: STDIO)
#   --host HOST         HTTP host (default: 0.0.0.0)
#   --port PORT         HTTP port (default: 8000)
```

### Verify Server is Running

```bash
# For HTTP mode, check health endpoint
curl http://localhost:8000/health

# Or check MCP endpoint
curl http://localhost:8000/mcp/v1/tools
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/compliance-gate.yml`:

```yaml
name: Compliance Gate

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  compliance-check:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout code
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. Setup Python
      - name: Setup Python 3.10
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      # 3. Install uv
      - name: Install uv
        run: pip install uv

      # 4. Install dependencies
      - name: Install project dependencies
        run: uv sync

      # 5. Install OPA
      - name: Install OPA
        run: |
          curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
          chmod +x opa
          sudo mv opa /usr/local/bin/
          opa version

      # 6. Initialize evidence store
      - name: Initialize evidence store
        run: mkdir -p evidence_store/{events,sarif,decision_logs}

      # 7. Start FastMCP server in background
      - name: Start FastMCP server
        run: |
          python -m reqif_mcp --http --host 127.0.0.1 --port 8000 &
          sleep 5  # Wait for server to start

      # 8. Load ReqIF baseline
      - name: Load requirements baseline
        id: load_baseline
        run: |
          # Base64 encode ReqIF XML
          REQIF_B64=$(base64 -w 0 requirements/baseline.reqif)

          # Parse ReqIF via MCP tool
          RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/mcp/v1/tools/reqif.parse \
            -H "Content-Type: application/json" \
            -d "{\"xml_b64\": \"$REQIF_B64\", \"policy_baseline_id\": \"POL-2024.01\", \"policy_baseline_version\": \"2024.01\"}")

          # Extract baseline handle
          HANDLE=$(echo $RESPONSE | jq -r '.handle')
          echo "BASELINE_HANDLE=$HANDLE" >> $GITHUB_ENV

      # 9. Run agent to extract facts
      - name: Run compliance agent
        id: run_agent
        run: |
          # Run stub agent for testing (replace with real agent in production)
          FACTS=$(python agents/stub_agent.py --subtype CYBER)
          echo "$FACTS" > /tmp/agent_facts.json

      # 10. Evaluate with OPA
      - name: Evaluate compliance
        id: evaluate
        run: |
          # Query requirements by subtype
          REQUIREMENTS=$(curl -s -X POST http://127.0.0.1:8000/mcp/v1/tools/reqif.query \
            -H "Content-Type: application/json" \
            -d "{\"handle\": \"$BASELINE_HANDLE\", \"subtypes\": [\"CYBER\"]}")

          # Evaluate each requirement (simplified example)
          # In production, use Python script to orchestrate evaluation
          python scripts/evaluate_requirements.py \
            --baseline-handle "$BASELINE_HANDLE" \
            --facts-file /tmp/agent_facts.json \
            --bundle-path opa-bundles/example

      # 11. Generate SARIF report
      - name: Generate SARIF report
        run: |
          # SARIF generated by evaluate_requirements.py script
          # Verify SARIF file exists
          ls -lh evidence_store/sarif/*.sarif

      # 12. Upload SARIF to GitHub
      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: evidence_store/sarif/*.sarif
          category: compliance-gate

      # 13. Publish SARIF as artifact
      - name: Upload SARIF artifact
        uses: actions/upload-artifact@v3
        with:
          name: sarif-reports
          path: evidence_store/sarif/*.sarif

      # 14. Check compliance gate status
      - name: Check compliance gate
        run: |
          # Parse SARIF to check for errors
          ERRORS=$(jq '[.runs[].results[] | select(.level == "error")] | length' evidence_store/sarif/*.sarif)

          if [ "$ERRORS" -gt 0 ]; then
            echo "❌ Compliance gate FAILED: $ERRORS error(s) found"
            exit 1
          else
            echo "✅ Compliance gate PASSED"
          fi
```

### GitLab CI/CD Example

Create `.gitlab-ci.yml`:

```yaml
compliance-gate:
  stage: test
  image: python:3.10

  before_script:
    - pip install uv
    - uv sync
    - curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
    - chmod +x opa && mv opa /usr/local/bin/
    - mkdir -p evidence_store/{events,sarif,decision_logs}

  script:
    # Start FastMCP server
    - python -m reqif_mcp --http --host 127.0.0.1 --port 8000 &
    - sleep 5

    # Run compliance evaluation (using helper script)
    - python scripts/run_compliance_gate.py

    # Check for failures
    - |
      ERRORS=$(jq '[.runs[].results[] | select(.level == "error")] | length' evidence_store/sarif/*.sarif)
      if [ "$ERRORS" -gt 0 ]; then
        echo "Compliance gate FAILED: $ERRORS error(s)"
        exit 1
      fi

  artifacts:
    reports:
      sast: evidence_store/sarif/*.sarif
    paths:
      - evidence_store/
```

---

## Containerized Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install OPA
RUN curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64 && \
    chmod +x /usr/local/bin/opa

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY reqif_mcp/ ./reqif_mcp/
COPY schemas/ ./schemas/
COPY opa-bundles/ ./opa-bundles/
COPY agents/ ./agents/

# Install Python dependencies
RUN uv sync --frozen

# Create evidence store directories
RUN mkdir -p evidence_store/{events,sarif,decision_logs}

# Expose HTTP port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OPA_BINARY_PATH=/usr/local/bin/opa
ENV EVIDENCE_STORE_PATH=/app/evidence_store
ENV OPA_BUNDLE_PATH=/app/opa-bundles/example

# Run FastMCP server with HTTP transport
CMD ["python", "-m", "reqif_mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run Container

```bash
# Build Docker image
docker build -t reqif-opa-mcp:latest .

# Run container (HTTP mode)
docker run -d \
  --name reqif-mcp-server \
  -p 8000:8000 \
  -v $(pwd)/evidence_store:/app/evidence_store \
  reqif-opa-mcp:latest

# Check container logs
docker logs reqif-mcp-server

# Stop container
docker stop reqif-mcp-server
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  reqif-mcp-server:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./evidence_store:/app/evidence_store
      - ./opa-bundles:/app/opa-bundles:ro
    environment:
      - OPA_BINARY_PATH=/usr/local/bin/opa
      - EVIDENCE_STORE_PATH=/app/evidence_store
      - OPA_BUNDLE_PATH=/app/opa-bundles/example
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Run with:

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Configuration Options

### Environment Variables

The system can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPA_BINARY_PATH` | Path to OPA binary | `opa` (in PATH) |
| `OPA_BUNDLE_PATH` | Path to OPA bundle directory | `opa-bundles/example` |
| `EVIDENCE_STORE_PATH` | Path to evidence store directory | `evidence_store` |
| `MCP_SERVER_HOST` | HTTP server host | `0.0.0.0` |
| `MCP_SERVER_PORT` | HTTP server port | `8000` |
| `DECISION_LOG_PATH` | Path to decision logs file | `evidence_store/decision_logs/decisions.jsonl` |
| `VERIFICATION_LOG_PATH` | Path to verification events file | `evidence_store/events/verifications.jsonl` |

### Setting Environment Variables

```bash
# Linux/macOS
export OPA_BINARY_PATH=/usr/local/bin/opa
export OPA_BUNDLE_PATH=/opt/opa-bundles/production

# Windows (PowerShell)
$env:OPA_BINARY_PATH="C:\Program Files\opa\opa.exe"
$env:OPA_BUNDLE_PATH="C:\opa-bundles\production"
```

### OPA Bundle Configuration

Place OPA bundles in the configured bundle path:

```
opa-bundles/
├── example/                    # Example bundle (for testing)
│   ├── .manifest
│   ├── policy/
│   │   └── cyber.rego
│   └── data/
│       └── thresholds.json
└── production/                 # Production bundle
    ├── .manifest
    ├── policy/
    │   ├── cyber.rego
    │   ├── access_control.rego
    │   └── data_privacy.rego
    └── data/
        ├── thresholds.json
        └── lookup_tables.json
```

### Evidence Store Configuration

The evidence store requires these subdirectories:

```
evidence_store/
├── events/                     # Verification events (JSONL)
│   └── verifications.jsonl
├── sarif/                      # SARIF reports (JSON)
│   └── {evaluation_id}.sarif
└── decision_logs/              # OPA decision logs (JSONL)
    └── decisions.jsonl
```

Ensure proper permissions:

```bash
# Set ownership (replace user:group as needed)
chown -R app:app evidence_store/

# Set permissions (read/write for app, read for others)
chmod -R 755 evidence_store/
chmod 644 evidence_store/**/*.jsonl
```

---

## Troubleshooting

### Server Won't Start

**Symptom**: `python -m reqif_mcp` fails with import errors

**Solutions**:
1. Verify dependencies are installed: `uv sync`
2. Check Python version: `python --version` (must be 3.10+)
3. Activate virtual environment: `source .venv/bin/activate`
4. Reinstall dependencies: `rm -rf .venv && uv sync`

### OPA Binary Not Found

**Symptom**: `OPA binary not found at path: opa`

**Solutions**:
1. Install OPA: `brew install opa` or download from OPA website
2. Verify installation: `which opa` and `opa version`
3. Set explicit path: `export OPA_BINARY_PATH=/usr/local/bin/opa`

### OPA Evaluation Fails

**Symptom**: `OPA evaluation failed: package not found`

**Solutions**:
1. Verify bundle path: `ls -R $OPA_BUNDLE_PATH`
2. Check bundle structure: ensure `policy/` and `.manifest` exist
3. Verify package name in requirement rubric matches Rego package declaration
4. Test bundle manually: `opa eval --bundle $OPA_BUNDLE_PATH --format pretty 'data'`

### SARIF Validation Errors

**Symptom**: `SARIF validation failed: invalid schema`

**Solutions**:
1. Verify SARIF schema exists: `ls schemas/sarif-schema-2.1.0.json`
2. Check SARIF output structure with: `jq . evidence_store/sarif/*.sarif`
3. Validate manually: `python -c "from reqif_mcp import validate_sarif_file; print(validate_sarif_file('evidence_store/sarif/test.sarif').unwrap())"`

### Evidence Store Permission Errors

**Symptom**: `Permission denied: evidence_store/events/verifications.jsonl`

**Solutions**:
1. Check directory permissions: `ls -ld evidence_store/`
2. Fix ownership: `chown -R $USER evidence_store/`
3. Fix permissions: `chmod -R 755 evidence_store/`
4. Verify writable: `touch evidence_store/test && rm evidence_store/test`

### Port Already in Use

**Symptom**: `Address already in use: 0.0.0.0:8000`

**Solutions**:
1. Find process using port: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)
2. Kill process: `kill -9 <PID>`
3. Use different port: `python -m reqif_mcp --http --port 8080`

### Docker Container Crashes

**Symptom**: Container exits immediately after start

**Solutions**:
1. Check container logs: `docker logs reqif-mcp-server`
2. Run interactively: `docker run -it --rm reqif-opa-mcp:latest /bin/bash`
3. Verify OPA installation: `docker exec reqif-mcp-server opa version`
4. Check volume mounts: `docker inspect reqif-mcp-server`

### Type Checking Errors

**Symptom**: `mypy --strict` reports type errors

**Solutions**:
1. Update type stubs: `uv add --dev types-jsonschema`
2. Regenerate uv.lock: `uv lock`
3. Clear mypy cache: `rm -rf .mypy_cache`
4. Run with verbose output: `uv run mypy --strict --show-traceback reqif_mcp/`

### Linting Errors

**Symptom**: `ruff check` reports errors

**Solutions**:
1. Auto-fix errors: `uv run ruff check --fix`
2. Check specific file: `uv run ruff check reqif_mcp/server.py`
3. Ignore specific rule: Add `# noqa: <rule>` comment

### Test Failures

**Symptom**: `pytest` fails

**Solutions**:
1. Run specific test: `uv run pytest tests/test_reqif_parser.py -v`
2. Show captured output: `uv run pytest -s`
3. Skip OPA tests if OPA not installed: `uv run pytest -k "not opa"`
4. Update test fixtures: Check `tests/fixtures/` for outdated data

### FastMCP Server Timeout

**Symptom**: MCP tool calls timeout or hang

**Solutions**:
1. Increase timeout in client configuration
2. Check server logs for errors
3. Verify OPA evaluations complete: `opa eval` manually
4. Reduce requirement set size for testing
5. Check for infinite loops in Rego policies

### Integration Test Skipped

**Symptom**: `pytest` skips integration tests

**Solutions**:
1. Verify OPA installed: `which opa`
2. Check skip condition: `pytest --collect-only`
3. Force run: Remove `@pytest.mark.skipif` decorator temporarily
4. Use mock mode: Run `test_e2e_without_opa` test instead

---

## Additional Resources

- **ReqIF Specification**: https://www.omg.org/spec/ReqIF/
- **OPA Documentation**: https://www.openpolicyagent.org/docs/latest/
- **SARIF Specification**: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **Project README**: [README.md](../README.md)
- **Agent Runner Interface**: [agent-runner-interface.md](./agent-runner-interface.md)
- **SARIF Mapping Rules**: [sarif-mapping.md](./sarif-mapping.md)
- **Evidence Store**: [evidence-store.md](./evidence-store.md)

---

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Consult the project README.md
- Review the comprehensive documentation in `docs/`
