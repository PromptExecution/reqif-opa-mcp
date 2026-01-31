#!/usr/bin/env python3
"""Create a new PRD (Product Requirements Document) JSON file.

Usage:
    python ralph/create_prd.py "Project Name" "Branch Name" "Description" > ralph/prd.json
    
Or interactively:
    python ralph/create_prd.py --interactive > ralph/prd.json
"""

import json
import sys
from typing import Any, Dict, List


def create_user_story(
    story_id: str,
    title: str,
    description: str,
    acceptance_criteria: List[str],
    priority: int,
) -> Dict[str, Any]:
    """Create a user story dictionary."""
    return {
        "id": story_id,
        "title": title,
        "description": description,
        "acceptanceCriteria": acceptance_criteria,
        "priority": priority,
        "passes": False,
        "notes": "",
    }


def create_prd(
    project: str,
    branch_name: str,
    description: str,
    user_stories: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a PRD dictionary."""
    return {
        "project": project,
        "branchName": branch_name,
        "description": description,
        "userStories": user_stories,
    }


def interactive_mode() -> Dict[str, Any]:
    """Interactively create a PRD."""
    print("=== Ralph PRD Creator (Interactive Mode) ===", file=sys.stderr)
    print("", file=sys.stderr)
    
    project = input("Project name: ")
    branch_name = input("Branch name (e.g., ralph/feature-name): ")
    description = input("Project description: ")
    
    print("", file=sys.stderr)
    print("Now enter user stories. Press Ctrl+D (or Ctrl+Z on Windows) when done.", file=sys.stderr)
    print("", file=sys.stderr)
    
    user_stories: List[Dict[str, Any]] = []
    story_num = 1
    
    while True:
        try:
            print(f"--- User Story {story_num} ---", file=sys.stderr)
            story_id = input(f"Story ID (default: US-{story_num:03d}): ").strip() or f"US-{story_num:03d}"
            title = input("Title: ")
            if not title:
                break
            
            desc = input("Description: ")
            
            print("Acceptance criteria (one per line, empty line to finish):", file=sys.stderr)
            criteria = []
            while True:
                criterion = input("  - ")
                if not criterion:
                    break
                criteria.append(criterion)
            
            priority = input(f"Priority (default: {story_num}): ").strip()
            priority_int = int(priority) if priority else story_num
            
            user_stories.append(
                create_user_story(story_id, title, desc, criteria, priority_int)
            )
            
            story_num += 1
            print("", file=sys.stderr)
            
        except (EOFError, KeyboardInterrupt):
            break
    
    print("", file=sys.stderr)
    print(f"✅ Created PRD with {len(user_stories)} user stories", file=sys.stderr)
    
    return create_prd(project, branch_name, description, user_stories)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--interactive", "-i"]:
        prd = interactive_mode()
    elif len(sys.argv) >= 4:
        # Command line mode
        project = sys.argv[1]
        branch_name = sys.argv[2]
        description = sys.argv[3]
        
        # Create empty PRD with placeholder story
        user_stories = [
            create_user_story(
                "US-001",
                "Initial user story",
                "Replace this with actual user stories",
                ["Add acceptance criteria here", "Typecheck passes"],
                1,
            )
        ]
        
        prd = create_prd(project, branch_name, description, user_stories)
        print(
            "ℹ️  Created PRD template. Edit ralph/prd.json to add user stories.",
            file=sys.stderr,
        )
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    
    # Output JSON to stdout
    print(json.dumps(prd, indent=2))


if __name__ == "__main__":
    main()
