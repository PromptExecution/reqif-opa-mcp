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
