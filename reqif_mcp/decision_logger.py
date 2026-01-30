"""
Decision logging module for OPA evaluations.

Provides append-only JSONL logging of all OPA policy evaluations for audit trail.
Each evaluation produces a log entry with unique ID, inputs, outputs, timestamp, and policy version.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from returns.result import Failure, Result, Success
from ulid import ULID


class DecisionLogEntry(TypedDict):
    """Decision log entry structure."""

    evaluation_id: str
    timestamp: str
    requirement: dict[str, Any]
    facts: dict[str, Any]
    context: dict[str, Any]
    decision: dict[str, Any]
    policy: dict[str, Any]


def create_decision_log_entry(
    requirement: dict[str, Any],
    facts: dict[str, Any],
    decision: dict[str, Any],
    context: dict[str, Any] | None = None,
    evaluation_id: str | None = None,
) -> DecisionLogEntry:
    """
    Create a decision log entry from evaluation inputs and outputs.

    Args:
        requirement: Requirement record that was evaluated
        facts: Agent facts used in evaluation
        decision: OPA decision output
        context: Optional evaluation context
        evaluation_id: Optional evaluation ID (ULID generated if not provided)

    Returns:
        DecisionLogEntry with all required fields
    """
    if evaluation_id is None:
        evaluation_id = str(ULID())

    if context is None:
        context = {}

    # Extract policy provenance from decision
    policy = decision.get("policy", {})

    entry: DecisionLogEntry = {
        "evaluation_id": evaluation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "requirement": requirement,
        "facts": facts,
        "context": context,
        "decision": decision,
        "policy": policy,
    }

    return entry


def append_decision_log(
    entry: DecisionLogEntry,
    log_file_path: Path | str | None = None,
) -> Result[str, Exception]:
    """
    Append a decision log entry to JSONL log file.

    Args:
        entry: Decision log entry to write
        log_file_path: Path to log file (defaults to evidence_store/decision_logs/decisions.jsonl)

    Returns:
        Success with evaluation_id if written successfully, Failure with exception on error
    """
    if log_file_path is None:
        # Default to evidence_store/decision_logs/decisions.jsonl relative to cwd
        log_file_path = Path.cwd() / "evidence_store" / "decision_logs" / "decisions.jsonl"
    else:
        log_file_path = Path(log_file_path)

    try:
        # Create parent directory if it doesn't exist
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Append entry as single JSON line
        with open(log_file_path, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")

        return Success(entry["evaluation_id"])

    except (OSError, IOError, PermissionError) as e:
        return Failure(
            Exception(f"Failed to write decision log to {log_file_path}: {e}")
        )
    except (TypeError, ValueError) as e:
        return Failure(Exception(f"Failed to serialize decision log entry: {e}"))


def log_evaluation(
    requirement: dict[str, Any],
    facts: dict[str, Any],
    decision: dict[str, Any],
    context: dict[str, Any] | None = None,
    log_file_path: Path | str | None = None,
    evaluation_id: str | None = None,
) -> Result[str, Exception]:
    """
    Create and append a decision log entry in one operation.

    Convenience function that combines create_decision_log_entry and append_decision_log.

    Args:
        requirement: Requirement record that was evaluated
        facts: Agent facts used in evaluation
        decision: OPA decision output
        context: Optional evaluation context
        log_file_path: Optional path to log file
        evaluation_id: Optional evaluation ID (ULID generated if not provided)

    Returns:
        Success with evaluation_id if logged successfully, Failure with exception on error
    """
    entry = create_decision_log_entry(
        requirement=requirement,
        facts=facts,
        decision=decision,
        context=context,
        evaluation_id=evaluation_id,
    )

    return append_decision_log(entry, log_file_path)
