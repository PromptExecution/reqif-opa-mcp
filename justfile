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

test-junit out="artifacts/tests/junit.xml":
    mkdir -p "$(dirname {{out}})"
    uv run pytest -v --junitxml "{{out}}"

lint:
    uv run ruff check .

fmt:
    uv run ruff format .

typecheck:
    uv run mypy reqif_mcp reqif_ingest_cli

check: lint typecheck test

check-ingest:
    just -f reqif_ingest_cli/justfile check

check-all: check check-ingest

ci-check out="artifacts/tests/junit.xml":
    just lint
    just typecheck
    just test-junit "{{out}}"

dogfood-ingest:
    just -f reqif_ingest_cli/justfile smoke-aemo-core
    just -f reqif_ingest_cli/justfile smoke-aemo-toolkit

selftest-ingest out="artifacts/selftest/ingest":
    mkdir -p "{{out}}"
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli distill \
        "samples/aemo/The AESCSF v2 Core.xlsx" \
        --pretty > "{{out}}/aescsf-core.candidates.json"
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli emit-reqif \
        "samples/aemo/The AESCSF v2 Core.xlsx" \
        --title "AESCSF Core Derived Baseline" \
        --output "{{out}}/aescsf-core.reqif" \
        --pretty > "{{out}}/aescsf-core.emit.json"
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli distill \
        "samples/aemo/V2 AESCSF Toolkit Version V1-1.xlsx" \
        --pretty > "{{out}}/aescsf-toolkit.candidates.json"
    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli emit-reqif \
        "samples/aemo/V2 AESCSF Toolkit Version V1-1.xlsx" \
        --title "AESCSF Toolkit Derived Baseline" \
        --output "{{out}}/aescsf-toolkit.reqif" \
        --pretty > "{{out}}/aescsf-toolkit.emit.json"

repo-security-facts out="artifacts/selftest/repo-security-facts.json":
    mkdir -p "$(dirname {{out}})"
    env UV_CACHE_DIR=.uv-cache uv run python agents/repo_security_agent.py --root . > {{out}}

dogfood-asvs out="artifacts/selftest/asvs":
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

selftest-asvs out="artifacts/selftest/asvs":
    just dogfood-asvs {{out}}

dogfood-asvs-cwe cwe out="":
    #!/usr/bin/env bash
    set -euo pipefail
    OUTPUT="{{out}}"
    if [ -z "$OUTPUT" ]; then
        OUTPUT="artifacts/selftest/asvs-{{cwe}}"
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

dogfood-ssdf out="artifacts/selftest/ssdf":
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

selftest-ssdf out="artifacts/selftest/ssdf":
    just dogfood-ssdf {{out}}

dogfood-security:
    just dogfood-asvs
    just dogfood-ssdf

selftest-security:
    just selftest-asvs
    just selftest-ssdf

selftest-suite out="artifacts/selftest" enforce="true":
    #!/usr/bin/env bash
    set -euo pipefail
    OUT="{{out}}"
    ENFORCE="{{enforce}}"
    STATUS=0
    mkdir -p "$OUT"

    set +e
    just selftest-ingest "$OUT/ingest"
    RC=$?
    [ "$RC" -eq 0 ] || STATUS=$RC

    just selftest-asvs "$OUT/asvs"
    RC=$?
    [ "$RC" -eq 0 ] || STATUS=$RC

    just selftest-ssdf "$OUT/ssdf"
    RC=$?
    [ "$RC" -eq 0 ] || STATUS=$RC
    set -e

    env UV_CACHE_DIR=.uv-cache uv run python scripts/write_artifact_summary.py \
        --mode selftest \
        --root "$OUT" \
        --summary-markdown "$OUT/selftest_summary.md" \
        --summary-json "$OUT/selftest_summary.json"

    if [ "$ENFORCE" = "true" ] && [ "$STATUS" -ne 0 ]; then
        exit "$STATUS"
    fi
    exit 0

demo-artifacts out="artifacts/demo" selftest_out="artifacts/selftest" enforce="false":
    #!/usr/bin/env bash
    set -euo pipefail
    OUT="{{out}}"
    SELFTEST_OUT="{{selftest_out}}"
    ENFORCE="{{enforce}}"
    STATUS=0
    mkdir -p "$OUT/reqif" "$OUT/selftest"

    set +e
    just selftest-suite "$SELFTEST_OUT" false
    RC=$?
    [ "$RC" -eq 0 ] || STATUS=$RC
    set -e

    rm -rf "$OUT/selftest"
    mkdir -p "$OUT/selftest"
    cp -R "$SELFTEST_OUT"/. "$OUT/selftest/"

    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli emit-reqif \
        "samples/aemo/The AESCSF v2 Core.xlsx" \
        --title "AESCSF Core Derived Baseline" \
        --output "$OUT/reqif/aescsf-core.reqif" \
        --pretty > "$OUT/reqif/aescsf-core.emit.json"

    env UV_CACHE_DIR=.uv-cache uv run python -m reqif_ingest_cli emit-reqif \
        "samples/aemo/V2 AESCSF Toolkit Version V1-1.xlsx" \
        --title "AESCSF Toolkit Derived Baseline" \
        --output "$OUT/reqif/aescsf-toolkit.reqif" \
        --pretty > "$OUT/reqif/aescsf-toolkit.emit.json"

    env UV_CACHE_DIR=.uv-cache uv run python scripts/write_artifact_summary.py \
        --mode demo \
        --root "$OUT" \
        --summary-markdown "$OUT/demo_summary.md" \
        --summary-json "$OUT/demo_summary.json"

    if [ "$ENFORCE" = "true" ] && [ "$STATUS" -ne 0 ]; then
        exit "$STATUS"
    fi
    exit 0

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
