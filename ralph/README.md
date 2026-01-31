# Ralph++ Autonomous Agent System

Ralph++ is an enhanced autonomous coding agent that reads PRD specifications, implements features, and manages a continuous workflow by automatically transitioning between completed work and new GitHub issues.

## How Ralph Works

Ralph++ follows a continuous autonomous workflow:

1. **Check for local PRD**: Looks for `ralph/prd.json` with incomplete user stories
2. **Implement user stories**: Picks the highest priority incomplete story and implements it
3. **Quality checks**: Runs typecheck, lint, and tests before committing
4. **Commit with conventional format**: Uses `<type>(<scope>): <description>` format
5. **Update PRD**: Marks completed story as `passes: true`
6. **Log progress**: Appends implementation details and learnings to `progress.txt`
7. **Archive completed PRD**: When all stories pass, archives `prd.json` to `.archive/` with timestamp
8. **Fetch next work**: Checks for new local PRD, then fetches most recent open GitHub issue
9. **Convert issue to PRD**: Parses GitHub issue into `prd.json` format and repeats workflow
10. **Exit when done**: When no local PRD exists and no open issues remain, Ralph exits cleanly

After completing all stories in a PRD, the file is archived to `.archive/prd-YYYYMMDD-HHMMSS-project-name.json` to preserve history while allowing fresh work to begin.

## Backlog Workflow

Ralph++ processes work in this priority order:

1. **Local prd.json** (highest priority)
   - If `ralph/prd.json` exists with incomplete stories (`passes: false`), continue working on it
   - Manual PRDs always take precedence over automated GitHub issue conversion

2. **GitHub Issues** (medium priority)
   - If no local prd.json exists, fetch the most recently created open issue
   - Convert issue to prd.json format and begin implementation
   - Branch naming: `gh-issue-{number}-{title-kebab-case}`

3. **Exit cleanly** (lowest priority)
   - If no local prd.json and no open GitHub issues, Ralph exits with success
   - Displays: `✅ BACKLOG CLEAR - All issues completed!`
   - No infinite loops or waiting states

This ensures manual PRDs are never overwritten by automated issue fetching, and Ralph stops when all work is complete.

## Archive Management

Completed PRD files are archived with timestamps for historical tracking:

**Archive Directory Structure:**
```
ralph/
├── .archive/
│   ├── prd-20260131-143022-ralph-plus-plus.json
│   ├── prd-20260131-151500-health-endpoint-fix.json
│   └── prd-20260131-163000-user-authentication.json
├── prd.json (current work)
├── progress.txt
└── *.py (automation scripts)
```

**Archive Naming Convention:**
- Format: `prd-YYYYMMDD-HHMMSS-project-name.json`
- Timestamp: When archival occurred (local time)
- Project name: Extracted from `prd.json` `project` field, kebab-cased

**Example Archive Listing:**
```bash
$ ls .archive/
prd-20260131-143022-ralph-plus-plus.json
prd-20260131-151500-fix-health-endpoint-ci-failure.json
prd-20260131-163000-user-authentication-module.json
```

**Archive Configuration:**
- `.archive/` directory is added to `.gitignore` by default
- Users can override to commit archived PRDs if desired
- Archival only occurs when ALL user stories have `passes: true`

## Conventional Commit Format

Ralph uses conventional commits for all work:

**Format:** `<type>(<scope>): <description>`

**Types:**
- `feat`: New feature implementation
- `fix`: Bug fix
- `docs`: Documentation changes
- `chore`: Maintenance tasks

**Scope:** User story ID (e.g., `US-005`, `US-042`)

**Examples:**
```
feat(US-005): update ralph instructions with archival workflow
fix(US-012): handle missing gh cli gracefully
docs(US-006): add ralph++ workflow to CLAUDE.md
chore(US-001): archive completed prd.json files
```

**Commit Body:** Includes acceptance criteria summary

**Commit Footer:**
- `Closes #<issue-number>` (if from GitHub issue)
- `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`

## Pull Request Creation

When all user stories from a GitHub issue are completed, Ralph automatically creates a pull request:

**PR Title:** `feat: <issue-title>` or `fix: <issue-title>`

**PR Body Template:**
```markdown
## Summary
- Implemented US-001: Feature description
- Implemented US-002: Another feature
- Implemented US-003: Final feature

## Testing
- Typecheck: ✅ passes
- Lint (ruff): ✅ passes
- Tests: ✅ all passing

Closes #<issue-number>

🤖 Generated with Claude Code
```

**Requirements:**
- Only creates PR when on feature branch (not main/master)
- Auto-detects default branch (main or master)
- Returns PR URL in completion message
- PR created after marking last story as `passes: true`

## Progress Logging

Ralph maintains a detailed progress log at `ralph/progress.txt`:

**Entry Format:**
```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

**Codebase Patterns Section:**
The top of `progress.txt` consolidates reusable patterns:
```
## Codebase Patterns
- Example: Use `sql<number>` template for aggregations
- Example: Always use `IF NOT EXISTS` for migrations
- Example: Export types from actions.ts for UI components
```

Only general, reusable patterns are added here (not story-specific details).

## Automation Scripts

Ralph++ includes Python scripts for workflow automation:

- **archive_prd.py**: Archives completed prd.json to `.archive/`
- **check_prd.py**: Validates prd.json and checks for incomplete stories
- **fetch_github_issue.py**: Fetches most recent open GitHub issue using `gh` CLI
- **convert_issue_to_prd.py**: Converts GitHub issue to prd.json format
- **commit_formatter.py**: Generates conventional commit messages from user stories
- **create_pr.py**: Creates GitHub pull request when issue is complete
- **log_issue_completion.py**: Logs issue completion summary to progress.txt
- **check_backlog.py**: Checks if backlog is clear (no local prd.json and no open issues)

**Usage Examples:**
```bash
# Generate commit message for US-007
uv run python ralph/commit_formatter.py US-007

# Use in git commit
git commit -m "$(uv run python ralph/commit_formatter.py US-007)"

# Log issue completion
uv run python ralph/log_issue_completion.py ralph/prd.json https://github.com/org/repo/pull/123

# Check if backlog is clear
uv run python ralph/check_backlog.py
# Exit code 0: Backlog clear (no work remaining)
# Exit code 1: Work remaining (local prd.json or open issues)
# Exit code 2: Error checking backlog
```

**Requirements:**
- Python 3.11+
- GitHub CLI (`gh`) installed and authenticated
- `returns` module for error handling
- Type hints with mypy --strict compliance

## GitHub Issue Template

Use `.github/ISSUE_TEMPLATE/ralph-feature.md` for Ralph-compatible issues:

**Structure:**
```markdown
## Problem
[Describe the problem]

## Goal
[Describe the desired outcome]

## User Stories

### US-001: First feature
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

### US-002: Second feature
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
```

Ralph automatically parses this format into prd.json.

## Troubleshooting

**GitHub CLI not found:**
```
Error: gh command not found
Solution: Install GitHub CLI from https://cli.github.com/
```

**GitHub CLI authentication:**
```
Error: gh auth status failed
Solution: Run `gh auth login` to authenticate
```

**No issues found:**
```
✅ BACKLOG CLEAR - All issues completed!
Ralph++ has processed all work items. Job complete.
```

This is expected when all work is done. Ralph exits cleanly.

**Archive directory permissions:**
```
Error: Cannot create .archive/ directory
Solution: Ensure write permissions in ralph/ directory
```

## Quality Requirements

All commits must pass:
- **Typecheck**: Python scripts with mypy --strict
- **Lint**: ruff (NEVER black or other linters)
- **Tests**: Project-specific test suite

Ralph will NOT commit broken code.

## Exit Conditions

Ralph exits when:
1. All user stories in current PRD have `passes: true` AND
2. No new local prd.json exists AND
3. No open GitHub issues remain

**Completion Message:**
```
✅ BACKLOG CLEAR - All issues completed!
Ralph++ has processed all work items. Job complete.
Completed PRDs archived in .archive/: 5
```

Exit code: 0 (success)
