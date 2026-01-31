#!/usr/bin/env python3
"""Create GitHub pull request when issue completion is detected.

Automatically creates a PR when all user stories from a GitHub issue are complete.
Uses gh CLI for PR creation and targets the default branch.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Literal

from returns.result import Failure, Result, Success

PRType = Literal["feat", "fix", "docs", "chore"]


def get_pr_type_from_stories(user_stories: list[Dict[str, Any]]) -> PRType:
    """Infer PR type from user story titles.

    Args:
        user_stories: List of user story dictionaries

    Returns:
        Appropriate PR type based on story content
    """
    titles = " ".join(story.get("title", "").lower() for story in user_stories)

    if any(keyword in titles for keyword in ["fix", "bug", "error", "issue"]):
        return "fix"
    elif any(keyword in titles for keyword in ["docs", "documentation", "readme"]):
        return "docs"
    elif any(keyword in titles for keyword in ["archive", "cleanup", "refactor"]):
        return "chore"
    else:
        return "feat"


def get_default_branch() -> Result[str, str]:
    """Get the default branch name for the repository.

    Returns:
        Success with branch name (main/master) or Failure with error message
    """
    try:
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        for line in result.stdout.split("\n"):
            if "HEAD branch:" in line:
                branch = line.split(":")[-1].strip()
                return Success(branch)
        return Failure("Could not determine default branch from git remote")
    except subprocess.CalledProcessError as e:
        return Failure(f"Failed to get default branch: {e.stderr}")
    except subprocess.TimeoutExpired:
        return Failure("Timeout getting default branch")
    except Exception as e:
        return Failure(f"Error getting default branch: {e}")


def get_current_branch() -> Result[str, str]:
    """Get the current branch name.

    Returns:
        Success with branch name or Failure with error message
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        branch = result.stdout.strip()
        if not branch:
            return Failure("Not on a branch (detached HEAD)")
        return Success(branch)
    except subprocess.CalledProcessError as e:
        return Failure(f"Failed to get current branch: {e.stderr}")
    except subprocess.TimeoutExpired:
        return Failure("Timeout getting current branch")
    except Exception as e:
        return Failure(f"Error getting current branch: {e}")


def check_gh_cli_available() -> Result[None, str]:
    """Check if gh CLI is installed and authenticated.

    Returns:
        Success if gh is available, Failure with error message otherwise
    """
    try:
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except FileNotFoundError:
        return Failure(
            "gh CLI not found. Install it from: https://cli.github.com/\n"
            "Or run: sudo apt install gh"
        )
    except subprocess.CalledProcessError:
        return Failure("gh CLI found but not working properly")
    except subprocess.TimeoutExpired:
        return Failure("Timeout checking gh CLI")

    # Check authentication
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return Success(None)
    except subprocess.CalledProcessError:
        return Failure(
            "gh CLI not authenticated. Run: gh auth login\n"
            "Or set GITHUB_TOKEN environment variable"
        )
    except subprocess.TimeoutExpired:
        return Failure("Timeout checking gh authentication")


def generate_pr_body(
    prd: Dict[str, Any], test_results: str = "All checks passed"
) -> str:
    """Generate PR body from PRD data.

    Args:
        prd: PRD dictionary containing user stories
        test_results: Test results summary

    Returns:
        Formatted PR body string
    """
    user_stories = prd.get("userStories", [])
    story_summary = []

    for story in user_stories:
        story_id = story.get("id", "")
        story_title = story.get("title", "")
        if story.get("passes", False):
            story_summary.append(f"- ✅ {story_id}: {story_title}")

    summary = "\n".join(story_summary) if story_summary else "No user stories completed"

    body_parts = ["## Summary", summary, "", "## Testing", test_results]

    # Add GitHub issue reference if available
    if "github_issue" in prd:
        issue_number = prd["github_issue"].get("number")
        if issue_number:
            body_parts.extend(["", f"Closes #{issue_number}"])

    return "\n".join(body_parts)


def create_pull_request(prd_path: Path) -> Result[str, str]:
    """Create a GitHub pull request for completed issue work.

    Args:
        prd_path: Path to prd.json file

    Returns:
        Success with PR URL or Failure with error message
    """
    # Check gh CLI availability
    gh_check = check_gh_cli_available()
    if isinstance(gh_check, Failure):
        return gh_check

    # Load PRD
    if not prd_path.exists():
        return Failure(f"PRD file not found: {prd_path}")

    try:
        with prd_path.open() as f:
            prd_data = json.load(f)
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON in PRD: {e}")

    # Verify all stories are complete
    user_stories = prd_data.get("userStories", [])
    if not all(story.get("passes", False) for story in user_stories):
        return Failure("Cannot create PR: not all user stories are complete")

    # Get current branch
    current_branch_result = get_current_branch()
    if isinstance(current_branch_result, Failure):
        return current_branch_result
    current_branch = current_branch_result.unwrap()

    # Get default branch
    default_branch_result = get_default_branch()
    if isinstance(default_branch_result, Failure):
        return default_branch_result
    default_branch = default_branch_result.unwrap()

    # Don't create PR if on default branch
    if current_branch in [default_branch, "main", "master"]:
        return Failure(f"Cannot create PR: currently on default branch '{current_branch}'")

    # Determine PR title
    pr_type = get_pr_type_from_stories(user_stories)
    issue_title = prd_data.get("project", "")
    if "github_issue" in prd_data:
        issue_title = prd_data["github_issue"].get("title", issue_title)

    pr_title = f"{pr_type}: {issue_title}"

    # Generate PR body
    pr_body = generate_pr_body(prd_data)

    # Create PR using gh CLI
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                pr_title,
                "--body",
                pr_body,
                "--base",
                default_branch,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        pr_url = result.stdout.strip()
        return Success(pr_url)
    except subprocess.CalledProcessError as e:
        return Failure(f"Failed to create PR: {e.stderr}")
    except subprocess.TimeoutExpired:
        return Failure("Timeout creating PR")
    except Exception as e:
        return Failure(f"Error creating PR: {e}")


def main() -> int:
    """CLI entry point for PR creation.

    Usage:
        python create_pr.py [prd-path]

    Defaults to ralph/prd.json if no path provided.
    """
    prd_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ralph/prd.json")

    result = create_pull_request(prd_path)

    match result:
        case Success(pr_url):
            print(f"✅ Pull request created: {pr_url}")
            return 0
        case Failure(error):
            print(f"❌ PR creation failed: {error}", file=sys.stderr)
            return 1
        case _:
            # Should never reach here due to Result type
            return 1


if __name__ == "__main__":
    sys.exit(main())
