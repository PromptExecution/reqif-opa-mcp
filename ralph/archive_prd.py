#!/usr/bin/env python3
"""Archive completed prd.json files to .archive/ directory."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    return text.lower().replace(" ", "-").replace("_", "-")


def all_stories_pass(prd: Dict[str, Any]) -> bool:
    """Check if all user stories have passes: true."""
    user_stories = prd.get("userStories", [])
    if not user_stories:
        return False
    return all(story.get("passes", False) for story in user_stories)


def archive_prd(prd_path: Path) -> Path:
    """Archive completed prd.json to .archive/ directory.

    Args:
        prd_path: Path to prd.json file

    Returns:
        Path to archived file

    Raises:
        ValueError: If PRD has incomplete stories
        FileNotFoundError: If prd.json doesn't exist
    """
    if not prd_path.exists():
        raise FileNotFoundError(f"PRD file not found: {prd_path}")

    # Load and validate PRD
    with open(prd_path, "r", encoding="utf-8") as f:
        prd = json.load(f)

    if not all_stories_pass(prd):
        raise ValueError("Cannot archive PRD with incomplete user stories")

    # Create .archive/ directory if it doesn't exist
    archive_dir = prd_path.parent / ".archive"
    archive_dir.mkdir(exist_ok=True)

    # Generate archive filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project_name = kebab_case(prd.get("project", "unknown"))
    archive_filename = f"prd-{timestamp}-{project_name}.json"
    archive_path = archive_dir / archive_filename

    # Move file to archive
    shutil.move(str(prd_path), str(archive_path))

    return archive_path


def main() -> None:
    """Main entry point for archival script."""
    ralph_dir = Path(__file__).parent
    prd_path = ralph_dir / "prd.json"

    try:
        archive_path = archive_prd(prd_path)
        print(f"✅ Archived completed PRD to: {archive_path}")
    except FileNotFoundError:
        print("ℹ️  No prd.json found - nothing to archive")
    except ValueError as e:
        print(f"⚠️  Cannot archive: {e}")
    except Exception as e:
        print(f"❌ Archive failed: {e}")
        raise


if __name__ == "__main__":
    main()
