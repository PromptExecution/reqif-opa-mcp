#!/usr/bin/env python3
"""Log completion of a GitHub issue to progress.txt.

This script appends a completion summary to ralph/progress.txt when all user stories
from a GitHub issue are completed. It includes timestamp, story count, files changed,
and PR link if available.

Usage:
    python ralph/log_issue_completion.py [prd_path] [pr_url]
    python ralph/log_issue_completion.py ralph/prd.json https://github.com/org/repo/pull/123

Exit codes:
    0: Success
    1: Error (prd.json not found, invalid format, missing github_issue property)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from returns.result import Failure, Result, Success


def load_prd(prd_path: Path) -> Result[dict[str, Any], str]:
    """Load and parse prd.json file.

    Args:
        prd_path: Path to prd.json file

    Returns:
        Result containing parsed PRD dict or error message
    """
    if not prd_path.exists():
        return Failure(f"PRD file not found: {prd_path}")

    try:
        with prd_path.open("r", encoding="utf-8") as f:
            prd_data = json.load(f)
        return Success(prd_data)
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON in {prd_path}: {e}")
    except Exception as e:
        return Failure(f"Failed to read {prd_path}: {e}")


def get_files_changed_count() -> Result[int, str]:
    """Get count of files changed in current git branch.

    Returns:
        Result containing file count or error message
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main...HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            # Try master if main doesn't exist
            result = subprocess.run(
                ["git", "diff", "--name-only", "master...HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                return Failure("Failed to get file diff (main/master not found)")

        files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return Success(len(files))
    except subprocess.TimeoutExpired:
        return Failure("git diff command timed out")
    except Exception as e:
        return Failure(f"Failed to get files changed: {e}")


def append_completion_log(
    prd_data: dict[str, Any], pr_url: str | None, progress_path: Path
) -> Result[None, str]:
    """Append issue completion summary to progress.txt.

    Args:
        prd_data: Parsed PRD data
        pr_url: Optional PR URL (if PR was created)
        progress_path: Path to progress.txt file

    Returns:
        Result indicating success or error message
    """
    github_issue = prd_data.get("github_issue")
    if not github_issue:
        return Failure("PRD missing github_issue property - not from GitHub issue")

    issue_number = github_issue.get("number")
    issue_title = github_issue.get("title", "Unknown")
    branch_name = prd_data.get("branchName", "unknown")
    user_stories = prd_data.get("userStories", [])
    total_stories = len(user_stories)

    # Get files changed count
    match get_files_changed_count():
        case Success(files_count):
            pass
        case Failure(error):
            files_count = "unknown"
            print(f"Warning: {error}", file=sys.stderr)
        case _:
            files_count = "unknown"

    # Format timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build completion log entry
    log_lines = [
        f"\n## ISSUE #{issue_number} COMPLETE - {issue_title}\n",
        f"Completed: {timestamp}\n",
        f"Total stories: {total_stories}\n",
        f"Files changed: {files_count}\n",
        f"Branch: {branch_name}\n",
    ]

    if pr_url:
        log_lines.append(f"PR: {pr_url}\n")

    log_lines.append("---\n")

    # Append to progress.txt
    try:
        with progress_path.open("a", encoding="utf-8") as f:
            f.writelines(log_lines)
        return Success(None)
    except Exception as e:
        return Failure(f"Failed to append to {progress_path}: {e}")


def print_error_and_exit(message: str) -> NoReturn:
    """Print error message and exit with code 1."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> NoReturn:
    """Main entry point."""
    # Parse command line arguments
    prd_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ralph/prd.json")
    pr_url = sys.argv[2] if len(sys.argv) > 2 else None

    progress_path = prd_path.parent / "progress.txt"

    # Load PRD
    match load_prd(prd_path):
        case Success(prd_data):
            pass
        case Failure(error):
            print_error_and_exit(error)
        case _:
            print_error_and_exit("Unexpected error loading PRD")

    # Append completion log
    match append_completion_log(prd_data, pr_url, progress_path):
        case Success(_):
            print(f"✅ Issue completion logged to {progress_path}")
            if pr_url:
                print(f"PR: {pr_url}")
            sys.exit(0)
        case Failure(error):
            print_error_and_exit(error)
        case _:
            print_error_and_exit("Unexpected error logging completion")


if __name__ == "__main__":
    main()
