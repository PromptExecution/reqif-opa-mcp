---
name: Ralph Feature Request
about: Create a structured feature request compatible with Ralph autonomous agent
title: "[Feature] "
labels: enhancement
assignees: ''
---

## Problem

<!-- Describe the problem or limitation you're facing -->

## Goal

<!-- What should be achieved by implementing this feature? -->

## User Stories

<!--
Format each user story as shown below. Ralph will parse these automatically.
Each user story should have:
- A unique ID in format US-XXX (e.g., US-001, US-042)
- A clear, actionable title
- A description explaining the user story
- Acceptance criteria as a checklist

Example:
-->

### US-001: Add health check endpoint

As a DevOps engineer, I need a health check endpoint so I can monitor service availability.

**Acceptance Criteria:**
- [ ] Create `/health` endpoint that returns 200 OK
- [ ] Endpoint returns JSON with status, version, and timestamp
- [ ] Add integration test for health endpoint
- [ ] Update API documentation
- [ ] Typecheck passes
- [ ] Lint passes

<!-- Add more user stories below following the same format -->

### US-002: Example second user story

As a [role], I need [feature] so that [benefit].

**Acceptance Criteria:**
- [ ] Specific, testable criterion 1
- [ ] Specific, testable criterion 2
- [ ] Typecheck passes
- [ ] Lint passes

## Additional Context

<!--
Add any additional context, screenshots, or references here.
Ralph will parse comments for additional requirements or clarifications.
-->

---

<!--
RALPH COMPATIBILITY NOTES:

1. User Story Format:
   - Must start with ### US-XXX: (three hashes, space, US-XXX:, space, title)
   - Alternative formats also supported: **US-XXX:** or ## US-XXX:

2. Acceptance Criteria Format:
   - Use GitHub checklists: - [ ] for unchecked, - [x] for checked
   - Place under each user story

3. Priority:
   - User stories are auto-assigned priority based on order (first = highest priority)

4. Branch Naming:
   - Ralph creates branch: gh-issue-{number}-{title-kebab-case}

5. Conventional Commits:
   - Ralph uses format: <type>(US-XXX): <description>
   - Types: feat, fix, docs, chore

6. Pull Requests:
   - Ralph auto-creates PR when all user stories complete
   - PR closes this issue automatically with "Closes #N"

For more details, see ralph/README.md in the repository.
-->
