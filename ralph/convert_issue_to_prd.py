#!/usr/bin/env python3
"""Convert GitHub issue (body + comments) to prd.json format."""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def kebab_case(text: str) -> str:
    """Convert text to kebab-case.

    Args:
        text: Input text to convert

    Returns:
        Kebab-cased string
    """
    # Remove special characters and replace spaces/underscores with hyphens
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text)
    # Remove consecutive hyphens
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def parse_user_stories(text: str) -> List[Dict[str, Any]]:
    """Parse user stories from issue body/comments.

    Looks for patterns:
    - ### US-XXX: Title
    - **US-XXX:** Title
    - ## US-XXX: Title

    Args:
        text: Issue body or comment text

    Returns:
        List of user story dictionaries with id, title, description
    """
    stories: List[Dict[str, Any]] = []

    # Pattern matches: ### US-001: Title or **US-001:** Title or ## US-001: Title
    pattern = r"(?:^|\n)(?:###?|#|\*\*)\s*(US-\d+)[:\s*]*\s*(.+?)(?:\*\*)?(?:\n|$)"

    matches = re.finditer(pattern, text, re.MULTILINE)

    for match in matches:
        story_id = match.group(1)
        title = match.group(2).strip()

        stories.append(
            {
                "id": story_id,
                "title": title,
                "description": "",  # Will be filled with context if found
                "acceptanceCriteria": [],
                "priority": len(stories) + 1,
                "passes": False,
                "notes": "",
            }
        )

    return stories


def parse_acceptance_criteria(text: str, story_id: str) -> List[str]:
    """Extract acceptance criteria checklist items for a user story.

    Looks for checklist items (- [ ] or - [x]) following a user story.

    Args:
        text: Text containing user stories and checklists
        story_id: User story ID to find criteria for

    Returns:
        List of acceptance criteria strings
    """
    criteria: List[str] = []

    # Find the story section
    story_pattern = rf"(?:^|\n)(?:###?|#|\*\*)\s*{re.escape(story_id)}[:\s*]*"
    match = re.search(story_pattern, text, re.MULTILINE)

    if not match:
        return criteria

    # Find text after this story until next story or end
    start_pos = match.end()
    next_story_pattern = r"(?:^|\n)(?:###?|#|\*\*)\s*US-\d+"
    next_match = re.search(next_story_pattern, text[start_pos:], re.MULTILINE)

    if next_match:
        section_text = text[start_pos : start_pos + next_match.start()]
    else:
        section_text = text[start_pos:]

    # Extract checklist items (- [ ] or - [x])
    checklist_pattern = r"^\s*-\s*\[[ xX]\]\s*(.+)$"
    for line in section_text.split("\n"):
        match = re.match(checklist_pattern, line)
        if match:
            criteria.append(match.group(1).strip())

    return criteria


def extract_description(text: str, story_id: str) -> str:
    """Extract description text between story header and acceptance criteria.

    Args:
        text: Text containing user stories
        story_id: User story ID

    Returns:
        Description string
    """
    # Find the story section
    story_pattern = rf"(?:^|\n)(?:###?|#|\*\*)\s*{re.escape(story_id)}[:\s*]*[^\n]*\n"
    match = re.search(story_pattern, text, re.MULTILINE)

    if not match:
        return ""

    start_pos = match.end()

    # Find text until first checklist item or next story
    next_story_pattern = r"(?:^|\n)(?:###?|#|\*\*)\s*US-\d+"
    checklist_pattern = r"^\s*-\s*\[[ xX]\]"

    section_lines = []
    for line in text[start_pos:].split("\n"):
        # Stop at next story
        if re.match(next_story_pattern, line):
            break
        # Stop at checklist
        if re.match(checklist_pattern, line):
            break
        # Collect non-empty lines
        if line.strip():
            section_lines.append(line.strip())

    return " ".join(section_lines)


def merge_comments_into_body(issue: Dict[str, Any]) -> str:
    """Merge issue body and all comments into single text.

    Args:
        issue: GitHub issue dictionary with body and comments

    Returns:
        Combined text of body and all comments
    """
    parts = []

    # Add issue body
    body = issue.get("body", "")
    if body:
        parts.append(body)

    # Add all comments
    comments = issue.get("comments", [])
    for comment in comments:
        comment_body = comment.get("body", "")
        if comment_body:
            parts.append(comment_body)

    return "\n\n".join(parts)


def convert_issue_to_prd(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GitHub issue to prd.json format.

    Args:
        issue: GitHub issue dictionary with number, title, body, comments

    Returns:
        PRD dictionary
    """
    issue_number = issue.get("number", 0)
    issue_title = issue.get("title", "Untitled Issue")

    # Merge body and comments
    full_text = merge_comments_into_body(issue)

    # Parse user stories
    stories = parse_user_stories(full_text)

    # If no explicit user stories found, create single story from issue
    if not stories:
        stories = [
            {
                "id": "US-001",
                "title": issue_title,
                "description": issue.get("body", "")[:200],  # First 200 chars
                "acceptanceCriteria": parse_acceptance_criteria(full_text, ""),
                "priority": 1,
                "passes": False,
                "notes": "",
            }
        ]
    else:
        # Fill in acceptance criteria and descriptions for each story
        for story in stories:
            story["acceptanceCriteria"] = parse_acceptance_criteria(
                full_text, story["id"]
            )
            story["description"] = extract_description(full_text, story["id"])

    # Generate branch name
    branch_name = f"gh-issue-{issue_number}-{kebab_case(issue_title)}"

    # Construct PRD
    prd = {
        "project": issue_title,
        "branchName": branch_name,
        "description": issue.get("body", "")[:500],  # First 500 chars as description
        "userStories": stories,
        "github_issue": {
            "number": issue_number,
            "url": f"https://github.com/{get_repo_slug()}/issues/{issue_number}",
            "title": issue_title,
        },
    }

    return prd


def get_repo_slug() -> str:
    """Get current repository owner/name from gh CLI.

    Returns:
        Repository slug in format 'owner/repo'
    """
    import subprocess

    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown/unknown"


def main() -> None:
    """Main entry point for issue-to-PRD conversion.

    Reads issue JSON from stdin or file path argument.
    Outputs prd.json to ralph/prd.json.
    """
    # Read issue data from stdin or file
    if len(sys.argv) > 1:
        # Read from file path argument
        issue_path = Path(sys.argv[1])
        if not issue_path.exists():
            print(f"❌ Issue file not found: {issue_path}", file=sys.stderr)
            sys.exit(1)

        with open(issue_path, "r", encoding="utf-8") as f:
            issue = json.load(f)
    else:
        # Read from stdin
        try:
            issue = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    # Convert issue to PRD
    try:
        prd = convert_issue_to_prd(issue)

        # Write to ralph/prd.json
        ralph_dir = Path(__file__).parent
        prd_path = ralph_dir / "prd.json"

        with open(prd_path, "w", encoding="utf-8") as f:
            json.dump(prd, f, indent=2)
            f.write("\n")  # Add trailing newline

        print(f"✅ Created prd.json from issue #{issue.get('number', 'unknown')}")
        print(f"   Project: {prd['project']}")
        print(f"   Branch: {prd['branchName']}")
        print(f"   User stories: {len(prd['userStories'])}")

    except Exception as e:
        print(f"❌ Conversion failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
