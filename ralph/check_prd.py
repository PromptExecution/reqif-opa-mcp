#!/usr/bin/env python3
"""Check for local prd.json before fetching GitHub issues."""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def load_prd(prd_path: Path) -> Optional[Dict[str, Any]]:
    """Load and validate prd.json file.

    Args:
        prd_path: Path to prd.json file

    Returns:
        Dictionary containing PRD data if valid, None otherwise
    """
    if not prd_path.exists():
        return None

    try:
        with open(prd_path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)

        # Basic validation: must have userStories array and be a dict
        if not isinstance(data, dict):
            print(f"⚠️  Invalid prd.json: not a JSON object", file=sys.stderr)
            return None

        prd: Dict[str, Any] = data
        if "userStories" not in prd or not isinstance(prd["userStories"], list):
            print(f"⚠️  Invalid prd.json: missing or invalid 'userStories' field", file=sys.stderr)
            return None

        return prd
    except json.JSONDecodeError as e:
        print(f"⚠️  Invalid JSON in prd.json: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️  Error reading prd.json: {e}", file=sys.stderr)
        return None


def count_incomplete_stories(prd: Dict[str, Any]) -> int:
    """Count user stories with passes: false.

    Args:
        prd: PRD dictionary

    Returns:
        Number of incomplete user stories
    """
    user_stories = prd.get("userStories", [])
    return sum(1 for story in user_stories if not story.get("passes", False))


def check_local_prd(ralph_dir: Path) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if local prd.json exists and has incomplete stories.

    Args:
        ralph_dir: Path to ralph directory

    Returns:
        Tuple of (should_continue_with_local, prd_data)
        - should_continue_with_local: True if local PRD exists with incomplete stories
        - prd_data: PRD dictionary if valid, None otherwise
    """
    prd_path = ralph_dir / "prd.json"
    prd = load_prd(prd_path)

    if prd is None:
        print("ℹ️  No local prd.json found, will check GitHub issues")
        return False, None

    incomplete_count = count_incomplete_stories(prd)

    if incomplete_count > 0:
        print(f"✅ Found local prd.json with {incomplete_count} incomplete stories")
        return True, prd
    else:
        print("ℹ️  Local prd.json exists but all stories are complete")
        return False, prd


def main() -> None:
    """Main entry point for prd checking."""
    ralph_dir = Path(__file__).parent
    should_continue, prd = check_local_prd(ralph_dir)

    if should_continue:
        print(f"Project: {prd.get('project', 'Unknown')}")  # type: ignore
        print("Continuing with local prd.json")
        sys.exit(0)
    else:
        print("Ready to check GitHub issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
