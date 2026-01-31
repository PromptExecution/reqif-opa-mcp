# Release Process

This document describes the idiomatic release workflow for ReqIF-OPA-MCP using `just` commands.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- [just](https://just.systems/) command runner installed
- [Docker](https://www.docker.com/) installed (for container builds)
- Write access to GitHub repository
- GitHub Container Registry (GHCR) authentication configured

## Quick Start

```bash
# Install dependencies
just install

# Run quality checks
just check

# Create a patch release (0.1.0 → 0.1.1)
just release patch

# Push the release to trigger CI/CD
just release-push
```

## Release Workflow

### 1. Prepare Release

Ensure all changes are committed and tests pass:

```bash
# Run all quality checks
just check

# Run tests with coverage
just test-coverage

# Validate OPA bundles
just opa-validate
```

### 2. Bump Version

Use semantic versioning to bump the version:

```bash
# Patch release (bug fixes): 0.1.0 → 0.1.1
just bump-version patch

# Minor release (new features): 0.1.0 → 0.2.0
just bump-version minor

# Major release (breaking changes): 0.1.0 → 1.0.0
just bump-version major
```

The `bump-version` command:
- Updates `version` in `pyproject.toml`
- Syncs `uv.lock` file
- Creates a git commit with the version bump
- Creates a git tag (e.g., `v0.1.1`)

### 3. Review Changes

```bash
# Check the commit
git show HEAD

# View the tag
git describe --tags

# Check version
just version
```

### 4. Push Release

```bash
# Push commit and tag to trigger CI/CD
just release-push
```

This pushes:
- The version bump commit to `main`
- The version tag (e.g., `v0.1.1`)

### 5. Monitor CI/CD

The GitHub Actions workflow automatically:
1. Builds Docker image for `linux/amd64` and `linux/arm64`
2. Tags image with version, major, minor, and SHA
3. Pushes to `ghcr.io/promptexecution/reqif-opa-mcp`
4. Generates build provenance attestation

Check progress:
```bash
# Open in browser
open https://github.com/PromptExecution/reqif-opa-mcp/actions

# Or use gh CLI
gh workflow view "Build and Push Docker Image"
gh run watch
```

## Docker Image Tags

Released images are tagged with:

| Tag Pattern | Example | Description |
|-------------|---------|-------------|
| `latest` | `latest` | Latest build from `main` branch |
| `{version}` | `0.1.1` | Specific version (from git tag `v0.1.1`) |
| `{major}.{minor}` | `0.1` | Rolling minor version tag |
| `{major}` | `0` | Rolling major version tag |
| `{branch}-{sha}` | `main-abc123d` | SHA tag for traceability |

## One-Step Release (Recommended)

```bash
# Bump version, commit, tag (but don't push)
just release patch  # or: minor, major

# Review, then push
just release-push
```

## Manual Docker Build (Local Testing)

```bash
# Build image locally
just docker-build latest

# Test the image
just docker-test latest

# Run container locally
just docker-run latest

# Push manually (if needed)
just docker-push latest
```

## Release Checklist

- [ ] All tests passing (`just test`)
- [ ] Code linted and formatted (`just check`)
- [ ] OPA bundles validated (`just opa-validate`)
- [ ] CHANGELOG.md updated (if exists)
- [ ] Documentation updated
- [ ] Version bumped appropriately (`just bump-version <level>`)
- [ ] Git tag created
- [ ] Changes pushed (`just release-push`)
- [ ] CI/CD pipeline succeeded
- [ ] Docker image available on GHCR
- [ ] Release notes created on GitHub (optional)

## Troubleshooting

### Authentication Failed

Ensure you're logged into GHCR:

```bash
# Using GitHub token
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Using gh CLI
gh auth token | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

### Build Failed in CI

1. Check workflow logs: `gh run view --log-failed`
2. Test build locally: `just docker-build test`
3. Fix issues and re-tag: `git tag -d v0.1.1 && just bump-version patch`

### Version Already Exists

Delete the tag locally and remotely:

```bash
# Delete local tag
git tag -d v0.1.1

# Delete remote tag
git push origin :refs/tags/v0.1.1

# Create new tag
just bump-version patch
```

## Development Workflow

### Local Development

```bash
# Install dependencies
just install

# Run server in STDIO mode
just dev

# Run server in HTTP mode
just serve

# Run with custom port
just serve 9000
```

### Quality Checks

```bash
# Run tests
just test

# Run linter
just lint

# Fix lint issues
just lint-fix

# Format code
just fmt

# Type check
just typecheck

# All checks
just check
```

### Docker Development

```bash
# Build image
just docker-build dev

# Run with local volumes
just docker-run dev 8000

# Test health
just docker-test dev
```

## Evidence Store Management

```bash
# View statistics
just evidence-stats

# Clean evidence store (with confirmation)
just clean-evidence
```

## Aliases

Common shortcuts defined in `justfile`:

| Alias | Command | Description |
|-------|---------|-------------|
| `just b` | `docker-build` | Build Docker image |
| `just r` | `docker-run` | Run Docker container |
| `just t` | `test` | Run tests |
| `just l` | `lint` | Run linter |
| `just f` | `fmt` | Format code |
| `just c` | `check` | Run all checks |
| `just d` | `dev` | Start dev server |
| `just s` | `serve` | Start HTTP server |

## Environment Variables

Configure via `.env` file (auto-loaded by justfile):

```bash
# Example .env
GITHUB_TOKEN=ghp_xxxxx
DOCKER_REGISTRY=ghcr.io
IMAGE_NAME=promptexecution/reqif-opa-mcp
```

## CI/CD Triggers

The Docker build workflow triggers on:

1. **Git tags**: `v*.*.*` (e.g., `v0.1.0`)
   - Builds and pushes versioned images
2. **Push to main**: 
   - Builds and pushes `latest` tag
3. **Pull requests**:
   - Builds only (no push) for validation
4. **Manual dispatch**:
   - Can be triggered manually from Actions UI

## Support

For issues or questions:
- GitHub Issues: https://github.com/PromptExecution/reqif-opa-mcp/issues
- Documentation: See README.md and CLAUDE.md
