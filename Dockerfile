# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.10
ARG OPA_VERSION=0.71.0

# Builder: Install Python deps
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY reqif_mcp/ reqif_mcp/
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev

# OPA binary
FROM alpine:latest AS opa-downloader
ARG OPA_VERSION
ARG TARGETARCH
WORKDIR /opa
RUN apk add --no-cache curl && \
    ARCH=${TARGETARCH:-amd64} && \
    curl -L -o /opa/opa "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${ARCH}_static" && \
    chmod +x /opa/opa

# Runtime
FROM python:${PYTHON_VERSION}-slim
LABEL org.opencontainers.image.title="ReqIF-OPA-MCP" \
      org.opencontainers.image.description="ReqIF compliance gate with OPA and SARIF" \
      org.opencontainers.image.vendor="PromptExecution" \
      org.opencontainers.image.source="https://github.com/PromptExecution/reqif-opa-mcp"

RUN groupadd -r reqif && useradd -r -g reqif -u 1000 reqif
WORKDIR /app
COPY --from=builder --chown=reqif:reqif /build/.venv /app/.venv
COPY --from=opa-downloader /opa/opa /usr/local/bin/opa
COPY --chown=reqif:reqif reqif_mcp/ /app/reqif_mcp/
COPY --chown=reqif:reqif pyproject.toml README.md LICENSE /app/
RUN mkdir -p /app/evidence_store/{events,sarif,decision_logs} /app/opa-bundles && \
    chown -R reqif:reqif /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER reqif
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from reqif_mcp.server import mcp; sys.exit(0)"
EXPOSE 8000
CMD ["python", "-m", "reqif_mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]
