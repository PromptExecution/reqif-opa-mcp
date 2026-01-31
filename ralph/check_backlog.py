#!/usr/bin/env python3
"""Check if Ralph++ backlog is clear (no local prd.json and no open issues).

Usage:
    python ralph/check_backlog.py

Exit codes:
    0: Backlog clear (no work remaining)
    1: Work remaining (local prd.json or open issues)
    2: Error checking backlog
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from returns.result import Failure, Result, Success


def check_local_prd() -> bool:
    """Check if local prd.json exists.

    Returns:
        True if prd.json exists and is valid JSON, False otherwise
    """
    prd_path = Path("ralph/prd.json")
    if not prd_path.exists():
        return False

    try:
        with prd_path.open() as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def check_open_issues() -> Result[bool, str]:
    """Check if there are any open GitHub issues.

    Returns:
        Success(True) if open issues exist
        Success(False) if no open issues
        Failure with error message on command failure
    """
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--limit", "1", "--json", "number"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            if "gh: command not found" in result.stderr or "not found" in result.stderr:
                return Failure("gh CLI not installed")
            if "authentication" in result.stderr.lower() or "token" in result.stderr.lower():
                return Failure("gh authentication required")
            return Failure(f"gh command failed: {result.stderr.strip()}")

        issues = json.loads(result.stdout)
        return Success(len(issues) > 0)

    except subprocess.TimeoutExpired:
        return Failure("gh command timed out")
    except json.JSONDecodeError:
        return Failure("Invalid JSON from gh command")
    except FileNotFoundError:
        return Failure("gh CLI not found")
    except Exception as e:
        return Failure(f"Unexpected error: {e!s}")


def count_archived_prds() -> int:
    """Count archived PRD files.

    Returns:
        Number of files in .archive/ directory
    """
    archive_dir = Path("ralph/.archive")
    if not archive_dir.exists():
        return 0

    return len(list(archive_dir.glob("prd-*.json")))


def exit_backlog_clear() -> NoReturn:
    """Exit with backlog clear message."""
    archived_count = count_archived_prds()
    print("✅ BACKLOG CLEAR - All issues completed!")
    print("Ralph++ has processed all work items. Job complete.")
    if archived_count > 0:
        print(f"Completed PRDs archived in .archive/: {archived_count}")
    sys.exit(0)


def exit_work_remaining(reason: str) -> NoReturn:
    """Exit with work remaining message."""
    print(f"Work remaining: {reason}")
    sys.exit(1)


def exit_error(message: str) -> NoReturn:
    """Exit with error message."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(2)


def main() -> NoReturn:
    """Check backlog status and exit accordingly."""
    # Check for local prd.json first
    has_local_prd = check_local_prd()
    if has_local_prd:
        exit_work_remaining("Local prd.json exists with work to complete")

    # Check for open GitHub issues
    result = check_open_issues()
    match result:
        case Success(has_issues):
            if has_issues:
                exit_work_remaining("Open GitHub issues exist")
            else:
                exit_backlog_clear()
        case Failure(error):
            exit_error(error)
        case _:
            exit_error("Unexpected result type")


if __name__ == "__main__":
    main()
