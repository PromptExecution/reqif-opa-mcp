set dotenv-load
set export
set shell := ["bash", "-c"]

default:
    @just --list

# Dev
install:
    uv sync

dev:
    uv run python -m reqif_mcp

serve port="8000":
    uv run python -m reqif_mcp --http --port {{port}}

# Quality
test:
    uv run pytest -v

lint:
    uv run ruff check .

fmt:
    uv run ruff format .

typecheck:
    uv run mypy reqif_mcp/

check: lint typecheck test

check-ingest:
    just -f reqif_ingest_cli/justfile check

check-all: check check-ingest

dogfood-ingest:
    just -f reqif_ingest_cli/justfile smoke-aemo-core
    just -f reqif_ingest_cli/justfile smoke-aemo-toolkit

selftest-ingest:
    just dogfood-ingest

repo-security-facts out="tmp/repo-security-facts.json":
    mkdir -p "$(dirname {{out}})"
    env UV_CACHE_DIR=.uv-cache uv run python agents/repo_security_agent.py --root . > {{out}}

dogfood-asvs out="tmp/dogfood-asvs":
    mkdir -p {{out}}
    just repo-security-facts {{out}}/facts.json
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_mcp.compliance_gate \
        --reqif-path samples/standards/derived/owasp_asvs_cwe.reqif \
        --facts-path {{out}}/facts.json \
        --bundle-path opa-bundles/owasp-asvs-sample \
        --subtype APPSEC \
        --package asvs.python_secure_coding.v1 \
        --baseline-id OWASP-ASVS-SAMPLE \
        --baseline-version 5.0.0 \
        --out-dir {{out}}

selftest-asvs out="tmp/dogfood-asvs":
    just dogfood-asvs {{out}}

dogfood-asvs-cwe cwe out="":
    #!/usr/bin/env bash
    set -euo pipefail
    OUTPUT="{{out}}"
    if [ -z "$OUTPUT" ]; then
        OUTPUT="tmp/dogfood-asvs-{{cwe}}"
    fi
    mkdir -p "$OUTPUT"
    just repo-security-facts "$OUTPUT/facts.json"
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_mcp.compliance_gate \
        --reqif-path samples/standards/derived/owasp_asvs_cwe.reqif \
        --facts-path "$OUTPUT/facts.json" \
        --bundle-path opa-bundles/owasp-asvs-sample \
        --subtype APPSEC \
        --package asvs.python_secure_coding.v1 \
        --attribute-filter cwe={{cwe}} \
        --baseline-id OWASP-ASVS-SAMPLE \
        --baseline-version 5.0.0 \
        --out-dir "$OUTPUT"

selftest-asvs-cwe cwe out="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{out}}" ]; then
        just dogfood-asvs-cwe {{cwe}} "{{out}}"
    else
        just dogfood-asvs-cwe {{cwe}}
    fi

dogfood-ssdf out="tmp/dogfood-ssdf":
    mkdir -p {{out}}
    just repo-security-facts {{out}}/facts.json
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_mcp.compliance_gate \
        --reqif-path samples/standards/derived/nist_ssdf_dogfood.reqif \
        --facts-path {{out}}/facts.json \
        --bundle-path opa-bundles/nist-ssdf-sample \
        --subtype SECURE_SDLC \
        --package ssdf.secure_software.v1 \
        --baseline-id NIST-SSDF-SAMPLE \
        --baseline-version 1.1 \
        --out-dir {{out}}

selftest-ssdf out="tmp/dogfood-ssdf":
    just dogfood-ssdf {{out}}

dogfood-security:
    just dogfood-asvs
    just dogfood-ssdf

selftest-security:
    just selftest-asvs
    just selftest-ssdf

# Docker
docker-build tag="latest":
    docker build -t ghcr.io/promptexecution/reqif-opa-mcp:{{tag}} .

docker-run tag="latest" port="8000":
    docker run --rm -p {{port}}:8000 \
        -v $(pwd)/evidence_store:/app/evidence_store \
        -v $(pwd)/opa-bundles:/app/opa-bundles \
        ghcr.io/promptexecution/reqif-opa-mcp:{{tag}}

docker-push tag="latest":
    docker push ghcr.io/promptexecution/reqif-opa-mcp:{{tag}}

# Release
version:
    @uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

bump-version level:
    #!/usr/bin/env bash
    set -euo pipefail
    CURRENT=$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
    case "{{level}}" in
        major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
        minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
        patch) PATCH=$((PATCH + 1)) ;;
        *) echo "Use: major, minor, or patch"; exit 1 ;;
    esac
    NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
    sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
    uv sync
    git add pyproject.toml uv.lock
    git commit -m "chore: bump version to $NEW_VERSION"
    git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
    echo "✅ v$NEW_VERSION tagged. Run: just release-push"

release-push:
    #!/usr/bin/env bash
    set -euo pipefail
    LATEST_TAG=$(git describe --tags --abbrev=0)
    git push origin main
    git push origin "$LATEST_TAG"
    echo "✅ Pushed $LATEST_TAG"

release level="patch": (bump-version level)
    @echo "Review with 'git show', then: just release-push"
