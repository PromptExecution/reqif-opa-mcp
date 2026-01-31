#!/usr/bin/env python3
"""Format conventional commit messages for Ralph user story completion.

Generates commit messages in the format:
    <type>(<scope>): <description>

    <body>

    Closes #<issue-number>
    Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"""

import json
import sys
from pathlib import Path
from typing import Literal

from returns.result import Failure, Result, Success

CommitType = Literal["feat", "fix", "docs", "chore"]


def format_commit_message(
    commit_type: CommitType,
    story_id: str,
    title: str,
    acceptance_criteria: list[str],
    issue_number: int | None = None,
) -> Result[str, str]:
    """Format a conventional commit message.

    Args:
        commit_type: Type of commit (feat, fix, docs, chore)
        story_id: User story ID (e.g., "US-007")
        title: User story title (max 72 chars for subject line)
        acceptance_criteria: List of acceptance criteria for the body
        issue_number: Optional GitHub issue number for Closes footer

    Returns:
        Success with formatted commit message or Failure with error message
    """
    # Validate subject line length (type + scope + title should be <= 72 chars)
    subject = f"{commit_type}({story_id}): {title}"
    if len(subject) > 72:
        # Truncate title to fit within 72 char limit
        max_title_length = 72 - len(f"{commit_type}({story_id}): ")
        truncated_title = title[:max_title_length - 3] + "..."
        subject = f"{commit_type}({story_id}): {truncated_title}"

    # Format body with acceptance criteria
    body_lines = []
    if acceptance_criteria:
        for criterion in acceptance_criteria:
            # Remove checkbox markers if present
            clean_criterion = criterion.strip().removeprefix("- [ ]").removeprefix("- [x]").strip()
            body_lines.append(f"- {clean_criterion}")

    # Build footer
    footer_lines = []
    if issue_number is not None:
        footer_lines.append(f"Closes #{issue_number}")
    footer_lines.append("Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>")

    # Assemble complete message
    message_parts = [subject]
    if body_lines:
        message_parts.append("")  # Blank line before body
        message_parts.extend(body_lines)
    if footer_lines:
        message_parts.append("")  # Blank line before footer
        message_parts.extend(footer_lines)

    return Success("\n".join(message_parts))


def get_commit_type_from_story(story_title: str) -> CommitType:
    """Infer commit type from user story title.

    Args:
        story_title: User story title

    Returns:
        Appropriate commit type
    """
    title_lower = story_title.lower()

    if any(keyword in title_lower for keyword in ["fix", "bug", "error", "issue"]):
        return "fix"
    elif any(keyword in title_lower for keyword in ["docs", "documentation", "readme"]):
        return "docs"
    elif any(keyword in title_lower for keyword in ["archive", "update", "refactor", "cleanup"]):
        return "chore"
    else:
        return "feat"


def format_from_prd(prd_path: Path, story_id: str) -> Result[str, str]:
    """Generate commit message from prd.json for a specific user story.

    Args:
        prd_path: Path to prd.json file
        story_id: User story ID to format commit for

    Returns:
        Success with formatted commit message or Failure with error message
    """
    if not prd_path.exists():
        return Failure(f"PRD file not found: {prd_path}")

    try:
        with prd_path.open() as f:
            prd_data = json.load(f)
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON in PRD: {e}")

    # Find the user story
    story = None
    for user_story in prd_data.get("userStories", []):
        if user_story.get("id") == story_id:
            story = user_story
            break

    if story is None:
        return Failure(f"User story {story_id} not found in PRD")

    # Extract fields
    title = story.get("title", "")
    acceptance_criteria = story.get("acceptanceCriteria", [])
    commit_type = get_commit_type_from_story(title)

    # Check if this PRD came from a GitHub issue
    issue_number = None
    if "github_issue" in prd_data:
        issue_number = prd_data["github_issue"].get("number")

    return format_commit_message(
        commit_type=commit_type,
        story_id=story_id,
        title=title,
        acceptance_criteria=acceptance_criteria,
        issue_number=issue_number,
    )


def main() -> int:
    """CLI entry point for commit message formatting.

    Usage:
        python commit_formatter.py <story-id> [prd-path]

    Defaults to ralph/prd.json if no path provided.
    """
    if len(sys.argv) < 2:
        print("Usage: python commit_formatter.py <story-id> [prd-path]", file=sys.stderr)
        print("Example: python commit_formatter.py US-007", file=sys.stderr)
        return 1

    story_id = sys.argv[1]
    prd_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("ralph/prd.json")

    result = format_from_prd(prd_path, story_id)

    match result:
        case Success(message):
            print(message)
            return 0
        case Failure(error):
            print(f"Error: {error}", file=sys.stderr)
            return 1
        case _:
            # Should never reach here due to Result type
            return 1


if __name__ == "__main__":
    sys.exit(main())
