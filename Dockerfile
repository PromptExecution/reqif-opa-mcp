# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.10
ARG OPA_VERSION=0.71.0

# Builder: install runtime-lite dependencies only.
FROM python:${PYTHON_VERSION}-slim AS deps-lite
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY reqif_mcp/ reqif_mcp/
COPY reqif_ingest_cli/ reqif_ingest_cli/
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev --extra ingest-lite

# OPA binary
FROM alpine:latest AS opa-downloader
ARG OPA_VERSION
ARG TARGETARCH
WORKDIR /opa
RUN apk add --no-cache curl && \
    ARCH=${TARGETARCH:-amd64} && \
    curl -L -o /opa/opa "https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${ARCH}_static" && \
    chmod +x /opa/opa

# Runtime-lite image: default CI/runtime target.
FROM python:${PYTHON_VERSION}-slim AS runtime-lite
LABEL org.opencontainers.image.title="ReqIF-OPA-MCP" \
      org.opencontainers.image.description="ReqIF compliance gate with OPA and SARIF (runtime-lite)" \
      org.opencontainers.image.vendor="PromptExecution" \
      org.opencontainers.image.source="https://github.com/PromptExecution/reqif-opa-mcp"

RUN groupadd -r reqif && useradd -r -g reqif -u 1000 reqif
WORKDIR /app
COPY --from=deps-lite --chown=reqif:reqif /build/.venv /app/.venv
COPY --from=opa-downloader /opa/opa /usr/local/bin/opa
COPY --chown=reqif:reqif reqif_mcp/ /app/reqif_mcp/
COPY --chown=reqif:reqif reqif_ingest_cli/ /app/reqif_ingest_cli/
COPY --chown=reqif:reqif agents/ /app/agents/
COPY --chown=reqif:reqif schemas/ /app/schemas/
COPY --chown=reqif:reqif samples/ /app/samples/
COPY --chown=reqif:reqif opa-bundles/ /app/opa-bundles/
COPY --chown=reqif:reqif justfile pyproject.toml README.md README-reqif-ingest-cli.md LICENSE /app/
RUN mkdir -p /app/evidence_store/{events,sarif,decision_logs} /app/artifacts/{tests,selftest,demo} && \
    chown -R reqif:reqif /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER reqif
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read(); sys.exit(0)"
EXPOSE 8000
CMD ["python", "-m", "reqif_mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]

# Builder: install full ingestion plus optional LLM review dependencies.
FROM deps-lite AS deps-full
RUN uv sync --frozen --no-dev --extra ingest-full --extra llm-review

# Ingest-full image for richer docling extraction.
FROM python:${PYTHON_VERSION}-slim AS ingest-full
LABEL org.opencontainers.image.title="ReqIF-OPA-MCP" \
      org.opencontainers.image.description="ReqIF compliance gate with OPA and SARIF (ingest-full)" \
      org.opencontainers.image.vendor="PromptExecution" \
      org.opencontainers.image.source="https://github.com/PromptExecution/reqif-opa-mcp"

RUN groupadd -r reqif && useradd -r -g reqif -u 1000 reqif
WORKDIR /app
COPY --from=deps-full --chown=reqif:reqif /build/.venv /app/.venv
COPY --from=opa-downloader /opa/opa /usr/local/bin/opa
COPY --chown=reqif:reqif reqif_mcp/ /app/reqif_mcp/
COPY --chown=reqif:reqif reqif_ingest_cli/ /app/reqif_ingest_cli/
COPY --chown=reqif:reqif agents/ /app/agents/
COPY --chown=reqif:reqif schemas/ /app/schemas/
COPY --chown=reqif:reqif samples/ /app/samples/
COPY --chown=reqif:reqif opa-bundles/ /app/opa-bundles/
COPY --chown=reqif:reqif justfile pyproject.toml README.md README-reqif-ingest-cli.md LICENSE /app/
RUN mkdir -p /app/evidence_store/{events,sarif,decision_logs} /app/artifacts/{tests,selftest,demo} && \
    chown -R reqif:reqif /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER reqif
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read(); sys.exit(0)"
EXPOSE 8000
CMD ["python", "-m", "reqif_mcp", "--http", "--host", "0.0.0.0", "--port", "8000"]

# Demo-full can carry sample/selftest assets while sharing ingest-full runtime.
FROM ingest-full AS demo-full

# Default build target stays lean.
FROM runtime-lite AS default
