# syntax=docker/dockerfile:1
# ReqIF-OPA-MCP Compliance Gate System
# Multi-stage build: builder + OPA + runtime

ARG PYTHON_VERSION=3.10
ARG OPA_VERSION=0.71.0

# ============================================================================
# Stage 1: Builder - Install dependencies with uv
# ============================================================================
FROM python:${PYTHON_VERSION}-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into /build/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY reqif_mcp/ reqif_mcp/
COPY README.md LICENSE ./

# Install the project itself
RUN uv sync --frozen --no-dev

# ============================================================================
# Stage 2: OPA Binary
# ============================================================================
FROM alpine:latest AS opa-downloader

ARG OPA_VERSION
ARG TARGETARCH

WORKDIR /opa

RUN apk add --no-cache curl && \
    ARCH=${TARGETARCH:-amd64} && \
    curl -L -o /opa/opa "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${ARCH}_static" && \
    chmod +x /opa/opa

# ============================================================================
# Stage 3: Runtime - Minimal Python image with app + OPA
# ============================================================================
FROM python:${PYTHON_VERSION}-slim

LABEL org.opencontainers.image.title="ReqIF-OPA-MCP" \
      org.opencontainers.image.description="ReqIF compliance gate system with OPA policy evaluation and SARIF reporting" \
      org.opencontainers.image.vendor="PromptExecution" \
      org.opencontainers.image.source="https://github.com/PromptExecution/reqif-opa-mcp" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN groupadd -r reqif && useradd -r -g reqif -u 1000 reqif

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=reqif:reqif /build/.venv /app/.venv

# Copy OPA binary
COPY --from=opa-downloader /opa/opa /usr/local/bin/opa

# Copy application code (if not already in .venv)
COPY --chown=reqif:reqif reqif_mcp/ /app/reqif_mcp/
COPY --chown=reqif:reqif pyproject.toml README.md LICENSE /app/

# Create directories for runtime data
RUN mkdir -p /app/evidence_store/{events,sarif,decision_logs} && \
    mkdir -p /app/opa-bundles && \
    chown -R reqif:reqif /app

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER reqif

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from reqif_mcp.server import mcp; sys.exit(0)"

# Expose HTTP port
EXPOSE 8000

# Default: Run HTTP server
CMD ["python", "-m", "reqif_mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]
