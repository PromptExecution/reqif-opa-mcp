# ReqIF-OPA-MCP Justfile
# Command runner for development, testing, and release workflows
# See: https://just.systems/man/en/

set dotenv-load
set export
set shell := ["bash", "-c"]

# Default recipe: show available commands
default:
    @just --list

# ============================================================================
# Development
# ============================================================================

# Install dependencies with uv
install:
    uv sync

# Run the MCP server in STDIO mode (local development)
dev:
    uv run python -m reqif_mcp

# Run the MCP server in HTTP mode
serve port="8000":
    uv run python -m reqif_mcp --http --port {{port}}

# ============================================================================
# Testing & Quality
# ============================================================================

# Run all tests
test:
    uv run pytest -v

# Run tests with coverage
test-coverage:
    uv run pytest --cov=reqif_mcp --cov-report=term --cov-report=html

# Run linting with ruff
lint:
    uv run ruff check .

# Fix auto-fixable lint issues
lint-fix:
    uv run ruff check --fix .

# Format code with ruff
fmt:
    uv run ruff format .

# Type check with mypy
typecheck:
    uv run mypy reqif_mcp/

# Run all quality checks
check: lint typecheck test

# ============================================================================
# Docker
# ============================================================================

# Build Docker image locally
docker-build tag="latest":
    docker build -t ghcr.io/promptexecution/reqif-opa-mcp:{{tag}} .

# Run Docker container locally
docker-run tag="latest" port="8000":
    docker run --rm -p {{port}}:8000 \
        -v $(pwd)/evidence_store:/app/evidence_store \
        -v $(pwd)/opa-bundles:/app/opa-bundles \
        ghcr.io/promptexecution/reqif-opa-mcp:{{tag}}

# Test Docker image health
docker-test tag="latest":
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🐳 Starting container..."
    CONTAINER_ID=$(docker run -d -p 8001:8000 ghcr.io/promptexecution/reqif-opa-mcp:{{tag}})
    
    echo "⏳ Waiting for health check..."
    sleep 5
    
    # Extract health status (avoid Go template syntax conflict)
    HEALTH_STATUS=$(docker inspect "$CONTAINER_ID" | grep -o '"Status": "[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [[ "$HEALTH_STATUS" == "healthy" ]] || docker ps --filter "id=$CONTAINER_ID" --filter "health=healthy" | grep -q "$CONTAINER_ID"; then
        echo "✅ Container is healthy"
        docker logs "$CONTAINER_ID"
        docker stop "$CONTAINER_ID"
        exit 0
    else
        echo "❌ Container health check failed (status: $HEALTH_STATUS)"
        docker logs "$CONTAINER_ID"
        docker stop "$CONTAINER_ID"
        exit 1
    fi

# Push Docker image to GHCR (requires authentication)
docker-push tag="latest":
    docker push ghcr.io/promptexecution/reqif-opa-mcp:{{tag}}

# ============================================================================
# Release Management
# ============================================================================

# Show current version from pyproject.toml
version:
    @uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

# Bump version (patch|minor|major) and create git tag
bump-version level:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Get current version
    CURRENT=$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
    echo "Current version: $CURRENT"
    
    # Parse version components
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
    
    # Bump appropriate component
    case "{{level}}" in
        major)
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH=0
            ;;
        minor)
            MINOR=$((MINOR + 1))
            PATCH=0
            ;;
        patch)
            PATCH=$((PATCH + 1))
            ;;
        *)
            echo "❌ Invalid level: {{level}} (use: major, minor, or patch)"
            exit 1
            ;;
    esac
    
    NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
    echo "New version: $NEW_VERSION"
    
    # Update pyproject.toml
    sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
    
    # Update uv.lock
    uv sync
    
    # Commit and tag
    git add pyproject.toml uv.lock
    git commit -m "chore: bump version to $NEW_VERSION"
    git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
    
    echo "✅ Version bumped to $NEW_VERSION"
    echo "📝 Review changes, then run: just release-push"

# Push release tag to trigger CI build
release-push:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Get latest tag
    LATEST_TAG=$(git describe --tags --abbrev=0)
    echo "📦 Pushing release tag: $LATEST_TAG"
    
    # Push commit and tag
    git push origin main
    git push origin "$LATEST_TAG"
    
    echo "✅ Release pushed! CI will build and publish Docker image."
    echo "🔗 Check status: https://github.com/PromptExecution/reqif-opa-mcp/actions"

# Full release workflow: bump, build, test, push
release level="patch": (bump-version level)
    @echo ""
    @echo "🚀 Release prepared. Next steps:"
    @echo "   1. Review the commit and tag"
    @echo "   2. Run: just release-push"
    @echo "   3. Monitor CI/CD pipeline"

# ============================================================================
# OPA Bundle Management
# ============================================================================

# Validate OPA bundle
opa-validate bundle="opa-bundles/example":
    opa test {{bundle}}

# Build OPA bundle with manifest
opa-build bundle="opa-bundles/example":
    opa build {{bundle}} -o bundle.tar.gz

# ============================================================================
# Evidence Store
# ============================================================================

# Clean evidence store (requires confirmation)
clean-evidence:
    #!/usr/bin/env bash
    read -p "⚠️  Delete all evidence store data? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf evidence_store/events/*
        rm -rf evidence_store/sarif/*
        rm -rf evidence_store/decision_logs/*
        echo "✅ Evidence store cleaned"
    else
        echo "❌ Cancelled"
    fi

# Show evidence store statistics
evidence-stats:
    #!/usr/bin/env bash
    echo "📊 Evidence Store Statistics"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Events:        $(find evidence_store/events -type f 2>/dev/null | wc -l)"
    echo "SARIF reports: $(find evidence_store/sarif -type f -name '*.sarif' 2>/dev/null | wc -l)"
    echo "Decision logs: $(find evidence_store/decision_logs -type f 2>/dev/null | wc -l)"
    echo ""
    echo "Total size:    $(du -sh evidence_store 2>/dev/null | cut -f1)"

# ============================================================================
# Aliases (b00t idiomatic shortcuts)
# ============================================================================

alias b := docker-build
alias r := docker-run
alias t := test
alias l := lint
alias f := fmt
alias c := check
alias d := dev
alias s := serve
