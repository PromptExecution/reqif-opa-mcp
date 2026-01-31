# Release Process

Release workflow using `just` commands.

## Quick Start

```bash
just check              # Quality checks
just release patch      # Bump version (0.1.0 → 0.1.1)
just release-push       # Push tag, trigger CI
```

## Commands

**Development:**
```bash
just install            # Install deps with uv
just dev                # STDIO server
just serve [port]       # HTTP server
just check              # lint + typecheck + test
```

**Release:**
```bash
just bump-version patch|minor|major  # Bump & tag
just release-push                    # Push tag
just version                         # Show version
```

**Docker:**
```bash
just docker-build [tag]   # Build image
just docker-run [tag]     # Run container
just docker-push [tag]    # Push to GHCR
```

## Release Workflow

1. `just check` - verify quality
2. `just release patch` - bump version, create tag
3. `git show` - review commit
4. `just release-push` - push to GitHub
5. CI builds and publishes to `ghcr.io/promptexecution/reqif-opa-mcp`

## Docker Tags

- `latest` - main branch
- `0.1.0` - version tag
- `0.1`, `0` - rolling tags
- `pr-15` - PR builds
- `sha-abc123d` - SHA tags

## Troubleshooting

**GHCR auth:**
```bash
gh auth token | docker login ghcr.io -u $USER --password-stdin
```

**Re-tag release:**
```bash
git tag -d v0.1.1
git push origin :refs/tags/v0.1.1
just bump-version patch
```

## CI Triggers

- Git tags `v*.*.*` → versioned release
- Push to main → latest tag
- PRs → build validation
