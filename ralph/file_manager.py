"""PRD and progress file management utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, TypeAlias

from returns.option import Nothing, Option, Some
from returns.result import Failure, Result, Success

PrdData: TypeAlias = Dict[str, Any]

PACKAGE_DIR = Path(__file__).resolve().parent
PRD_PATH = PACKAGE_DIR / "prd.json"
PROGRESS_PATH = PACKAGE_DIR / "progress.txt"


def read_prd() -> Result[PrdData, Exception]:
    """Load prd.json from disk."""

    try:
        raw = PRD_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return Failure(exc)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return Failure(exc)

    if not isinstance(data, dict):
        return Failure(ValueError("prd.json must contain a JSON object"))

    prd: PrdData = dict(data)
    return Success(prd)


def get_current_branch() -> Option[str]:
    """Return branchName from the current prd.json if present."""

    prd_result = read_prd()
    match prd_result:
        case Success(prd):
            pass
        case Failure(_):
            return Nothing

    branch_value = prd.get("branchName")
    if isinstance(branch_value, str) and branch_value.strip():
        return Some(branch_value)
    return Nothing


def initialize_progress_file() -> Result[Path, Exception]:
    """Ensure progress.txt exists for the current run."""

    try:
        if not PROGRESS_PATH.exists():
            PROGRESS_PATH.write_text("", encoding="utf-8")
    except OSError as exc:
        return Failure(exc)
    return Success(PROGRESS_PATH)


def append_to_progress(message: str) -> Result[None, Exception]:
    """Append a message to progress.txt."""

    init_result = initialize_progress_file()
    match init_result:
        case Success(_):
            pass
        case Failure(error):
            return Failure(error)

    try:
        with PROGRESS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(message)
            if not message.endswith("\n"):
                handle.write("\n")
    except OSError as exc:
        return Failure(exc)
    return Success(None)


__all__ = [
    "PROGRESS_PATH",
    "PRD_PATH",
    "append_to_progress",
    "get_current_branch",
    "initialize_progress_file",
    "read_prd",
]
