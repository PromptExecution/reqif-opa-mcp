#!/usr/bin/env python3
"""Fetch most recent open GitHub issue using gh CLI."""

import json
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


def check_gh_installed() -> bool:
    """Check if GitHub CLI (gh) is installed.

    Returns:
        True if gh is installed and available in PATH
    """
    return shutil.which("gh") is not None


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def fetch_latest_issue() -> Optional[Dict[str, Any]]:
    """Fetch the most recently created open GitHub issue.

    Returns:
        Issue data dictionary or None if no issues found

    Raises:
        RuntimeError: If gh command fails
        ValueError: If gh output is not valid JSON
    """
    # Fetch more issues and sort in Python since gh doesn't support --order/--sort in all versions
    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--limit",
        "100",
        "--json",
        "number,title,body,comments,createdAt",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        issues: List[Dict[str, Any]] = json.loads(result.stdout)

        if not issues:
            return None

        # Sort by createdAt descending (most recent first)
        sorted_issues = sorted(
            issues, key=lambda x: x.get("createdAt", ""), reverse=True
        )

        return sorted_issues[0]

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error"
        raise RuntimeError(f"gh issue list failed: {error_msg}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("gh issue list timed out after 30 seconds") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from gh CLI: {e}") from e


def main() -> None:
    """Main entry point for GitHub issue fetching."""
    # Check if gh CLI is installed
    if not check_gh_installed():
        print("❌ GitHub CLI (gh) is not installed")
        print("Install it from: https://cli.github.com/")
        print("Or use: brew install gh (macOS), apt install gh (Ubuntu), etc.")
        sys.exit(1)

    # Check if gh is authenticated
    if not check_gh_auth():
        print("❌ GitHub CLI is not authenticated")
        print("Run: gh auth login")
        print("Follow the prompts to authenticate with GitHub")
        sys.exit(1)

    # Fetch latest issue
    try:
        issue = fetch_latest_issue()

        if issue is None:
            print("✅ BACKLOG CLEAR - All issues completed!")
            sys.exit(0)

        # Output issue data as JSON for downstream processing
        print(f"✅ Found open issue #{issue['number']}: {issue['title']}")
        print(json.dumps(issue, indent=2))
        sys.exit(0)

    except RuntimeError as e:
        print(f"❌ Failed to fetch GitHub issues: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Invalid response from gh CLI: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
