# Ralph++ Fork Documentation

This document describes the Ralph++ fork enhancements to the base Ralph autonomous agent system.

## Overview

Ralph++ extends the base Ralph agent with automatic workflow orchestration between completed PRDs and GitHub issues, enabling continuous autonomous development until the backlog is clear.

**Base Ralph**: Single PRD execution (read prd.json → implement stories → stop)

**Ralph++**: Continuous workflow (read prd.json → implement → archive → fetch issue → convert → repeat → exit when backlog clear)

## Changes from Base Ralph

### 1. PRD Archival System

**Files Added:**
- `ralph/archive_prd.py` - Archives completed prd.json files with timestamps

**Behavior Change:**
- Base Ralph: Stops after completing all user stories in prd.json
- Ralph++: Moves completed prd.json to `.archive/prd-YYYYMMDD-HHMMSS-project-name.json`

**Usage:**
```bash
# Automatic archival when all stories have passes: true
uv run python ralph/archive_prd.py
```

### 2. Local PRD Priority Check

**Files Added:**
- `ralph/check_prd.py` - Validates and checks for incomplete local prd.json

**Behavior Change:**
- Base Ralph: Only works with local prd.json
- Ralph++: Checks for local prd.json first, then fetches GitHub issues if none exists

**Priority Order:**
1. Local `ralph/prd.json` with incomplete stories (`passes: false`)
2. GitHub issues (most recently created open issue)
3. Exit with backlog clear message

### 3. GitHub Issue Integration

**Files Added:**
- `ralph/fetch_github_issue.py` - Fetches most recent open GitHub issue via `gh` CLI
- `ralph/convert_issue_to_prd.py` - Converts GitHub issue to prd.json format

**Behavior Change:**
- Base Ralph: No GitHub integration
- Ralph++: Automatically converts GitHub issues to prd.json and executes them

**Issue Format:**
Issues should follow the template in `.github/ISSUE_TEMPLATE/ralph-feature.md`:
```markdown
### US-001: Feature title
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

### US-002: Another feature
- [ ] Another criterion
```

**Generated Branch Naming:**
- Format: `gh-issue-{number}-{title-kebab-case}`
- Example: `gh-issue-42-add-health-endpoint`

### 4. Conventional Commit Support

**Files Added:**
- `ralph/commit_formatter.py` - Generates conventional commit messages from prd.json

**Behavior Change:**
- Base Ralph: Generic commit messages
- Ralph++: Standardized conventional commits with co-author attribution

**Commit Format:**
```
<type>(<scope>): <description>

<acceptance criteria summary>

Closes #<issue-number>
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Usage:**
```bash
# Generate commit message for user story US-007
git commit -m "$(uv run python ralph/commit_formatter.py US-007)"
```

**Commit Type Inference:**
- `feat` - New feature (contains "add", "implement", "create")
- `fix` - Bug fix (contains "fix", "resolve", "correct")
- `docs` - Documentation (contains "document", "update docs")
- `chore` - Maintenance (everything else)

### 5. Automatic Pull Request Creation

**Files Added:**
- `ralph/create_pr.py` - Creates GitHub PRs when issue completed

**Behavior Change:**
- Base Ralph: No PR creation
- Ralph++: Automatically creates PR when all user stories from GitHub issue are complete

**PR Creation:**
- Title: `feat: <issue-title>` or `fix: <issue-title>` (type inferred from stories)
- Body includes: user story summary, test results, `Closes #<number>`
- Only created when on feature branch (not main/master)
- Returns PR URL for tracking

**Usage:**
```bash
# Automatic PR creation after marking last story as passes: true
uv run python ralph/create_pr.py
```

### 6. Issue Completion Logging

**Files Added:**
- `ralph/log_issue_completion.py` - Appends issue completion summary to progress.txt

**Behavior Change:**
- Base Ralph: Only per-story progress logging
- Ralph++: Additional issue-level completion log with metrics

**Completion Log Format:**
```
## ISSUE #42 COMPLETE - Add health endpoint
Completed: 2026-01-31 18:30:45
Total stories: 3
Files changed: 5
PR: https://github.com/org/repo/pull/123
Branch: gh-issue-42-add-health-endpoint
---
```

### 7. Backlog Clear Detection

**Files Added:**
- `ralph/check_backlog.py` - Checks for remaining work and exits gracefully

**Behavior Change:**
- Base Ralph: Stops after single PRD
- Ralph++: Continues until no local prd.json AND no open GitHub issues

**Exit Conditions:**
```
✅ BACKLOG CLEAR - All issues completed!
Ralph++ has processed all work items. Job complete.
Completed PRDs archived in .archive/: 5
```

**Exit Codes:**
- `0` - Backlog clear (no work remaining)
- `1` - Work remaining (local prd.json exists or open issues found)
- `2` - Error (gh CLI not installed, authentication failure, etc.)

### 8. GitHub Issue Template

**Files Added:**
- `.github/ISSUE_TEMPLATE/ralph-feature.md` - Standardized Ralph-compatible issue template

**Benefit:**
- Ensures GitHub issues are structured for optimal Ralph++ conversion
- Documents user story format, acceptance criteria, and workflow expectations
- Selectable when creating new issues on GitHub

## Configuration Options

### Archive Location

Default: `ralph/.archive/`

To change archive location, modify `ARCHIVE_DIR` in `ralph/archive_prd.py`:
```python
ARCHIVE_DIR = Path(__file__).parent / ".archive"
```

### GitHub Issue Filtering

By default, fetches most recently created open issue. To filter by labels, modify `ralph/fetch_github_issue.py`:
```bash
gh issue list --state open --label "ralph" --limit 1
```

### PR Settings

Default PR target branch: auto-detected (main or master)

To force specific target branch, modify `ralph/create_pr.py`:
```python
# Replace auto-detection with:
default_branch = "main"  # or "develop", etc.
```

## Files Modified from Base Ralph

**New Files Added:**
1. `ralph/archive_prd.py` - PRD archival
2. `ralph/check_prd.py` - PRD validation
3. `ralph/fetch_github_issue.py` - GitHub issue fetching
4. `ralph/convert_issue_to_prd.py` - Issue-to-PRD conversion
5. `ralph/commit_formatter.py` - Conventional commit generation
6. `ralph/create_pr.py` - PR creation
7. `ralph/log_issue_completion.py` - Issue completion logging
8. `ralph/check_backlog.py` - Backlog clear detection
9. `ralph/FORK.md` - This document
10. `.github/ISSUE_TEMPLATE/ralph-feature.md` - Issue template

**Updated Files:**
- `ralph/README.md` - Enhanced with Ralph++ workflow documentation
- `CLAUDE.md` - Added "Ralph++ Autonomous Workflow" section
- `ralph/progress.txt` - Progress log with learnings from all stories

**Unchanged Base Ralph Files:**
- All base Ralph agent instructions remain compatible
- No breaking changes to core Ralph workflow

## Syncing with Upstream

If maintaining this fork against upstream base Ralph repository:

### Initial Setup

```bash
# Add upstream remote
git remote add upstream <base-ralph-repo-url>

# Fetch upstream changes
git fetch upstream
```

### Sync Workflow

```bash
# Fetch latest upstream changes
git fetch upstream

# Merge upstream changes (resolve conflicts if needed)
git merge upstream/main

# Test that Ralph++ enhancements still work
uv run python ralph/check_backlog.py
uv run python ralph/create_pr.py --help
```

### Conflict Resolution

If upstream modifies files that Ralph++ also changed:

1. **CLAUDE.md**: Merge both sets of documentation (upstream + Ralph++)
2. **ralph/README.md**: Preserve Ralph++ sections, integrate upstream updates
3. **ralph/progress.txt**: Keep Ralph++ learnings, append upstream patterns

## Dependencies

Ralph++ adds these dependencies beyond base Ralph:

### Required:
- **GitHub CLI (`gh`)**: Issue fetching, PR creation, repository queries
  ```bash
  # Install on Ubuntu/Debian
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update
  sudo apt install gh

  # Authenticate
  gh auth login
  ```

- **Git**: Repository operations, branch management, file change tracking
- **Python 3.11+**: All Ralph++ scripts use modern Python features
- **uv**: Python package management (`uvx`, `uv run`)

### Python Packages:
All Python dependencies managed via `pyproject.toml`:
- `returns` - Result/Option types for error handling
- Standard library only (no additional packages required)

## Troubleshooting

### gh CLI Not Found

**Symptom:**
```
Error: gh CLI not installed
```

**Solution:**
Install GitHub CLI (see Dependencies section) and authenticate:
```bash
gh auth login
```

### Authentication Issues

**Symptom:**
```
Error: gh CLI authentication required
```

**Solution:**
```bash
# Re-authenticate with GitHub
gh auth login

# Or set token directly
export GITHUB_TOKEN=<your-token>
```

### No Open Issues but Ralph++ Continues

**Symptom:**
Ralph++ doesn't exit even when no issues exist

**Solution:**
Check for orphaned `ralph/prd.json`:
```bash
# If prd.json exists with incomplete stories, Ralph++ will continue
ls ralph/prd.json

# Archive it manually if needed
uv run python ralph/archive_prd.py

# Or delete it if invalid
rm ralph/prd.json
```

### PR Creation Fails on Main Branch

**Symptom:**
```
Error: Cannot create PR from default branch
```

**Solution:**
Ensure you're on a feature branch:
```bash
# Check current branch
git branch --show-current

# Create feature branch if needed
git checkout -b gh-issue-42-feature-name
```

### Issue Parsing Errors

**Symptom:**
Converted prd.json has malformed user stories

**Solution:**
- Ensure GitHub issues follow template format: `### US-XXX: Title`
- Acceptance criteria must use checklist format: `- [ ] criterion`
- If no user stories detected, check issue body and comments for format

### Archived PRDs Pile Up

**Symptom:**
`.archive/` directory contains many files

**Solution:**
Archive directory is append-only by design for audit trail. To clean:
```bash
# List archived PRDs
ls -lh ralph/.archive/

# Optional: Remove old archives (careful - permanent!)
find ralph/.archive/ -name "prd-*.json" -mtime +90 -delete
```

## Testing Fork-Specific Features

### Test PRD Archival
```bash
# Create test prd.json with all passes: true
echo '{"project":"test","userStories":[{"id":"US-001","passes":true}]}' > ralph/prd.json

# Archive it
uv run python ralph/archive_prd.py

# Verify archived
ls ralph/.archive/
```

### Test GitHub Issue Fetch
```bash
# Fetch most recent open issue
uv run python ralph/fetch_github_issue.py > test_issue.json

# Verify JSON output
cat test_issue.json | jq .
```

### Test Issue-to-PRD Conversion
```bash
# Convert test issue to prd.json
cat test_issue.json | uv run python ralph/convert_issue_to_prd.py > ralph/prd.json

# Verify PRD structure
cat ralph/prd.json | jq .
```

### Test Commit Formatter
```bash
# Create test prd.json with user story
echo '{"project":"test","userStories":[{"id":"US-001","title":"Add feature","acceptanceCriteria":["Test it"]}]}' > ralph/prd.json

# Generate commit message
uv run python ralph/commit_formatter.py US-001
```

### Test Backlog Check
```bash
# Check backlog status
uv run python ralph/check_backlog.py
echo $?  # 0 = clear, 1 = work remaining, 2 = error
```

## Fork Maintenance Checklist

When updating Ralph++:

- [ ] Test all automation scripts: `archive_prd.py`, `fetch_github_issue.py`, `convert_issue_to_prd.py`, `commit_formatter.py`, `create_pr.py`, `log_issue_completion.py`, `check_backlog.py`
- [ ] Run type checks: `mypy --strict ralph/*.py`
- [ ] Run linting: `ruff check ralph/`
- [ ] Verify GitHub issue template selectable in UI
- [ ] Test end-to-end workflow: manual prd.json → archive → fetch issue → convert → implement → create PR → backlog clear
- [ ] Update CLAUDE.md if workflow changes
- [ ] Update ralph/README.md if new scripts added
- [ ] Add learnings to ralph/progress.txt

## Support

For fork-specific issues:
- Check troubleshooting section above
- Review `ralph/progress.txt` for past learnings
- Consult `ralph/README.md` for automation script usage
- Check CLAUDE.md for Claude Code integration

For base Ralph issues:
- Refer to upstream repository documentation
- Check if issue exists in base Ralph before assuming fork-specific

## License

Ralph++ inherits the license from the base Ralph project. Check repository root for LICENSE file.
