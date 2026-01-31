# PRD: Ralph++ Workflow Enhancements

## Introduction

Enhance the Ralph autonomous agent system to automatically transition between completed PRDs and new GitHub issues, creating a continuous workflow until the backlog is clear. Ralph++ adds archival of completed work, GitHub issue integration, automatic PR creation with conventional commits, and treats "job complete" as when the entire backlog is empty.

This transforms Ralph from a single-PRD executor into a backlog-clearing autonomous system that can work through an entire project's issue queue.

## Goals

- Archive completed prd.json files to hidden `.archive/` directory with timestamps
- Automatically fetch and convert GitHub issues to prd.json format when current PRD is complete
- Prioritize local prd.json over fetching new GitHub issues
- Parse issue body + all comments to build comprehensive requirements
- Create pull requests with conventional commits when issues are completed
- Exit gracefully when backlog is clear (true "job done" state)
- Maintain backward compatibility with existing Ralph workflows
- Fork-friendly: changes isolated to ralph/ directory for easy forking

## User Stories

### US-001: Archive completed prd.json files
**Description:** As Ralph, when I complete all user stories in prd.json, I need to archive it so I can start fresh with the next issue while preserving history.

**Acceptance Criteria:**
- [ ] Create `.archive/` directory in ralph/ if it doesn't exist
- [ ] When all stories have `passes: true`, rename prd.json to `prd-[timestamp]-[project-name].json`
- [ ] Move renamed file to `.archive/prd-[timestamp]-[project-name].json`
- [ ] Timestamp format: `YYYYMMDD-HHMMSS` (e.g., `20260131-143022`)
- [ ] Project name extracted from prd.json `project` field, kebab-cased
- [ ] Add `.archive/` to .gitignore by default (user can override)
- [ ] Typecheck passes

### US-002: Check for local prd.json before fetching issues
**Description:** As Ralph, I need to prioritize local prd.json files over GitHub issues so manual PRDs take precedence.

**Acceptance Criteria:**
- [ ] Check if ralph/prd.json exists and is valid JSON
- [ ] If exists and has incomplete stories (`passes: false`), continue with that PRD
- [ ] Only attempt GitHub issue fetch if no local prd.json exists
- [ ] Log decision: "Found local prd.json with X incomplete stories" or "No local prd.json, checking GitHub issues"
- [ ] Typecheck passes

### US-003: Fetch most recent open GitHub issue
**Description:** As Ralph, when no local prd.json exists, I need to fetch the most recently created open issue so I can work on the latest priorities.

**Acceptance Criteria:**
- [ ] Use `gh issue list --state open --limit 1 --json number,title,body,comments,createdAt --order created --sort desc`
- [ ] If no issues found, exit with message: "✅ BACKLOG CLEAR - All issues completed!"
- [ ] Extract issue number, title, body, and all comments
- [ ] Handle `gh` command not found with clear error message
- [ ] Handle authentication errors with helpful guidance
- [ ] Typecheck passes

### US-004: Convert GitHub issue to prd.json format
**Description:** As Ralph, I need to convert a GitHub issue (body + comments) into a valid prd.json so I can execute it using the standard Ralph workflow.

**Acceptance Criteria:**
- [ ] Parse issue body for user stories in format `### US-XXX:` or `**US-XXX:**`
- [ ] Extract acceptance criteria from checklist items `- [ ]` under each user story
- [ ] Parse all comments for additional requirements or clarifications
- [ ] Generate prd.json with structure: `{project, branchName, description, userStories[]}`
- [ ] Branch name format: `gh-issue-[number]-[title-kebab-case]`
- [ ] Each user story includes: id, title, description, acceptanceCriteria[], priority, passes: false
- [ ] If no explicit user stories found, create single story from issue body
- [ ] Add property `github_issue: {number, url, title}` to prd.json for traceability
- [ ] Typecheck passes

### US-005: Update Ralph instructions with archival workflow
**Description:** As a developer using Ralph, I need the instructions updated to explain the new archival and GitHub issue workflow.

**Acceptance Criteria:**
- [ ] Update ralph/README.md "How Ralph Works" section with archival steps
- [ ] Document: "After completing all stories, prd.json is archived to `.archive/`"
- [ ] Document: "Ralph checks for new local prd.json, then GitHub issues, then exits"
- [ ] Add section "Backlog Workflow" explaining priority: local prd → GitHub issues → exit
- [ ] Add section "Archive Management" explaining .archive/ directory structure
- [ ] Include example: `ls .archive/` showing timestamped files
- [ ] Typecheck passes

### US-006: Update CLAUDE.md with Ralph++ workflow
**Description:** As Claude Code, I need CLAUDE.md updated so I understand the enhanced Ralph workflow when invoked.

**Acceptance Criteria:**
- [ ] Add section "Ralph++ Autonomous Workflow" to CLAUDE.md
- [ ] Document complete workflow: read prd → implement → archive → fetch issue → convert → repeat
- [ ] Document exit condition: "Ralph exits when backlog is clear (no local prd.json, no open issues)"
- [ ] Document conventional commit requirement for issue completion
- [ ] Document PR creation requirement when issue completed
- [ ] Include troubleshooting: gh CLI not installed, authentication issues
- [ ] Typecheck passes

### US-007: Add conventional commit formatting to Ralph
**Description:** As Ralph, when I complete a user story, I need to use conventional commit format so the commit history is standardized.

**Acceptance Criteria:**
- [ ] Commit message format: `<type>(<scope>): <description>`
- [ ] Types: feat (new feature), fix (bug fix), docs (documentation), chore (maintenance)
- [ ] Scope: user story ID (e.g., `feat(US-042): implement health endpoint`)
- [ ] Description: user story title, max 72 characters
- [ ] Body includes: user story acceptance criteria summary
- [ ] Footer includes: `Closes #<issue-number>` if from GitHub issue
- [ ] Footer includes: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`
- [ ] Typecheck passes

### US-008: Create pull request when issue completed
**Description:** As Ralph, when I complete all user stories from a GitHub issue, I need to create a PR automatically so the work can be reviewed and merged.

**Acceptance Criteria:**
- [ ] After marking last story as `passes: true`, create PR using `gh pr create`
- [ ] PR title: `feat: <issue-title>` or `fix: <issue-title>` based on content
- [ ] PR body includes: issue reference `Closes #<number>`, user story summary, test results
- [ ] PR body template: "## Summary\n[user stories completed]\n\n## Testing\n[test results]\n\nCloses #<number>"
- [ ] Use branch name from prd.json `branchName` field
- [ ] Target branch: main or master (auto-detect default branch)
- [ ] PR created only if on feature branch (not on main/master)
- [ ] Return PR URL in completion message
- [ ] Typecheck passes

### US-009: Handle no open issues gracefully
**Description:** As Ralph, when there are no open GitHub issues and no local prd.json, I need to exit cleanly indicating all work is complete.

**Acceptance Criteria:**
- [ ] Check: no ralph/prd.json exists
- [ ] Check: `gh issue list --state open --limit 1` returns empty
- [ ] Print: "✅ BACKLOG CLEAR - All issues completed!"
- [ ] Print: "Ralph++ has processed all work items. Job complete."
- [ ] Exit with code 0 (success)
- [ ] Log archived PRDs count: "Completed PRDs archived in .archive/: <count>"
- [ ] Do NOT enter infinite loop or wait state
- [ ] Typecheck passes

### US-010: Create GitHub issue template for Ralph compatibility
**Description:** As a project maintainer, I need a GitHub issue template that structures issues for optimal Ralph conversion.

**Acceptance Criteria:**
- [ ] Create `.github/ISSUE_TEMPLATE/ralph-feature.md`
- [ ] Template includes sections: Problem, Goal, User Stories, Acceptance Criteria
- [ ] User story format documented: `### US-XXX: Title`
- [ ] Acceptance criteria format: `- [ ] Specific criterion`
- [ ] Example issue included in template comments
- [ ] Template selectable when creating new issue on GitHub
- [ ] Typecheck passes

### US-011: Add progress.txt update for issue completion
**Description:** As Ralph, when I complete an issue, I need to append a completion summary to progress.txt before archiving.

**Acceptance Criteria:**
- [ ] Append to ralph/progress.txt: `## ISSUE #<number> COMPLETE - <title>`
- [ ] Include: completion timestamp, total stories, files changed count, PR link
- [ ] Format: `Completed: YYYY-MM-DD HH:MM:SS`
- [ ] Include: `PR: <url>` if PR was created
- [ ] Include: `Branch: <branch-name>` for traceability
- [ ] Separator line: `---` after each completion entry
- [ ] Typecheck passes

### US-012: Create ralph-plus-plus fork documentation
**Description:** As a developer forking Ralph++, I need clear documentation on what changed and how to maintain the fork.

**Acceptance Criteria:**
- [ ] Create ralph/FORK.md with fork-specific documentation
- [ ] Document all changes from base Ralph: archival, issue fetching, PR creation
- [ ] Include fork sync instructions: `git remote add upstream <base-ralph-repo>`
- [ ] Document configuration options: .archive/ location, issue labels, PR settings
- [ ] List files modified from base Ralph for easy diff tracking
- [ ] Include troubleshooting section for fork-specific issues
- [ ] Typecheck passes

## Functional Requirements

- FR-1: Ralph MUST archive completed prd.json to `.archive/prd-[timestamp]-[project].json` when all stories pass
- FR-2: Ralph MUST check for local prd.json before attempting to fetch GitHub issues
- FR-3: Ralph MUST fetch the most recently created open GitHub issue using `gh issue list`
- FR-4: Ralph MUST parse issue body and all comments to extract user stories and acceptance criteria
- FR-5: Ralph MUST generate valid prd.json from GitHub issue with traceability metadata
- FR-6: Ralph MUST use conventional commit format: `<type>(<scope>): <description>`
- FR-7: Ralph MUST create pull request automatically when all issue stories are complete
- FR-8: Ralph MUST exit with success when no local prd.json exists and no open issues remain
- FR-9: PR body MUST include `Closes #<issue-number>` to auto-close issue on merge
- FR-10: Archived PRDs MUST include timestamp and project name for easy identification
- FR-11: GitHub issue template MUST be provided in `.github/ISSUE_TEMPLATE/`
- FR-12: Progress.txt MUST log issue completion with timestamp and PR link

## Non-Goals (Out of Scope)

- No automatic merging of PRs (requires human review)
- No issue prioritization beyond "most recent" (no label-based priority)
- No multi-repo support (single repository workflow)
- No parallel issue processing (one at a time, sequential)
- No automatic issue creation from PRD failures
- No Slack/email notifications for completions
- No integration with project management tools (Jira, Linear, etc.)
- No automatic branch cleanup after PR merge

## Design Considerations

### Archive Directory Structure
```
ralph/
├── .archive/
│   ├── prd-20260131-143022-reqif-opa-sarif.json
│   ├── prd-20260201-091534-auth-system.json
│   └── prd-20260202-162847-ui-redesign.json
├── prd.json (current, if active)
├── progress.txt
└── README.md
```

### Issue to PRD Conversion Example

**GitHub Issue #42:**
```markdown
# Add user authentication

We need OAuth2 authentication for the API.

### US-001: OAuth2 configuration
- [ ] Add OAuth2 provider config
- [ ] Store client ID and secret in env vars

### US-002: Login endpoint
- [ ] POST /auth/login endpoint
- [ ] Return JWT token on success
```

**Generated prd.json:**
```json
{
  "project": "Add user authentication",
  "branchName": "gh-issue-42-add-user-authentication",
  "description": "We need OAuth2 authentication for the API.",
  "github_issue": {
    "number": 42,
    "url": "https://github.com/org/repo/issues/42",
    "title": "Add user authentication"
  },
  "userStories": [
    {
      "id": "US-001",
      "title": "OAuth2 configuration",
      "description": "As a developer, I need OAuth2 provider configuration so the system can authenticate users.",
      "acceptanceCriteria": [
        "Add OAuth2 provider config",
        "Store client ID and secret in env vars",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false
    },
    {
      "id": "US-002",
      "title": "Login endpoint",
      "description": "As a user, I need a login endpoint so I can authenticate and receive a token.",
      "acceptanceCriteria": [
        "POST /auth/login endpoint",
        "Return JWT token on success",
        "Typecheck passes"
      ],
      "priority": 2,
      "passes": false
    }
  ]
}
```

### Conventional Commit Format
```
feat(US-001): implement OAuth2 configuration

Added OAuth2 provider configuration with environment variable support
for client ID and secret. Configuration validates on startup.

Acceptance criteria:
- OAuth2 provider config added
- Client ID and secret stored in env vars
- Typecheck passes

Closes #42
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Pull Request Body Template
```markdown
## Summary
Completed GitHub issue #42: Add user authentication

Implemented OAuth2 authentication flow:
- US-001: OAuth2 configuration ✅
- US-002: Login endpoint ✅

## Testing
- All unit tests pass (42/42)
- Integration tests pass (12/12)
- Manual testing: OAuth2 flow verified with Google provider
- Typecheck: ✅ mypy --strict passes
- Linting: ✅ ruff check passes

## Changes
- Added OAuth2 provider configuration
- Implemented /auth/login endpoint with JWT response
- Added environment variable validation

Closes #42

🤖 Generated with Ralph++ autonomous agent
```

## Technical Considerations

### GitHub CLI Integration
- Requires `gh` CLI installed and authenticated
- Use `gh auth status` to verify authentication before issue fetch
- Handle rate limiting gracefully (GitHub API limits)
- Support both GitHub.com and GitHub Enterprise

### Error Handling
- `gh` not installed → clear error with installation instructions
- No authentication → guide to `gh auth login`
- API rate limit → wait and retry with exponential backoff
- Malformed issue body → create minimal single-story PRD with warning

### Branch Management
- Check if branch already exists before creating
- Use `git checkout -b` for new branches from main/master
- Detect default branch: `git symbolic-ref refs/remotes/origin/HEAD`
- PR targets default branch automatically

### Backward Compatibility
- Existing ralph/ directory structure unchanged
- Manual prd.json files still supported (higher priority than issues)
- Progress.txt format unchanged (append-only additions)
- No breaking changes to existing Ralph instructions

## Success Metrics

- Ralph successfully processes 10+ sequential issues without human intervention
- Archive directory contains complete history of all PRDs executed
- Pull requests created with <2 minutes overhead per issue completion
- Zero false positives for "backlog clear" state
- 100% conventional commit format compliance
- All PRs automatically link and close their source issues

## Open Questions

- Should Ralph support issue labels for filtering (e.g., only fetch issues labeled "ralph-ready")?
- Should `.archive/` be configurable via environment variable?
- Should Ralph support draft PRs initially, then convert to ready when tests pass?
- Should there be a dry-run mode to preview issue conversion without creating prd.json?
- Should Ralph support multi-issue batching (e.g., process 5 issues before creating PR)?
- Should archived PRDs be compressed (gzip) after 30 days to save space?

## Implementation Notes

### Testing Strategy
1. **Unit tests:** Issue parsing, prd.json generation, conventional commit formatting
2. **Integration tests:** Full workflow with mock GitHub API responses
3. **Manual tests:**
   - Create test issue on GitHub
   - Verify Ralph fetches and converts it
   - Verify PR creation with correct format
   - Verify archival and next issue fetch

### Rollout Plan
1. Implement archival (US-001) - low risk, isolated change
2. Implement issue fetching (US-003, US-004) - test with real issues
3. Implement PR creation (US-008) - test on feature branch
4. Update documentation (US-005, US-006, US-012)
5. Create issue template (US-010)
6. Full integration test with 3-5 sequential issues
7. Announce Ralph++ fork for community adoption

### Migration from Base Ralph
For existing Ralph users upgrading to Ralph++:
1. Copy ralph/ directory to your project
2. Run `mkdir ralph/.archive`
3. Add `.archive/` to `.gitignore`
4. Install and authenticate GitHub CLI: `gh auth login`
5. Create issues using provided template
6. Run Ralph as normal - new workflow activates automatically
