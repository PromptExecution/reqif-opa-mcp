"""Iteration runner for Ralph automation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TypeVar

from returns.result import Failure, Result

from ralph.config import RalphConfig, load_config
from ralph.executors import AmpExecutor, ClaudeExecutor, CodexExecutor, ToolExecutor
from ralph.logging_utils import (
    configure_logging,
    log_error,
    log_info,
    log_success,
    log_warning,
)

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
PROMPT_FILE = PROJECT_ROOT / "prompt.md"
CLAUDE_PROMPT_FILE = PROJECT_ROOT / "CLAUDE.md"
COMPLETE_MARKER = "<promise>COMPLETE</promise>"
ResultValue = TypeVar("ResultValue")


def _unwrap_result(result: Result[ResultValue, Exception], message: str) -> ResultValue:
    """Unwrap a Result or raise a chained error."""

    if isinstance(result, Failure):
        error = result.failure()
        raise RuntimeError(message) from error
    return result.unwrap()


def _build_executor(tool: str, config: RalphConfig) -> ToolExecutor:
    """Create the executor for the selected tool."""

    match tool:
        case "amp":
            return AmpExecutor(prompt_path=PROMPT_FILE, working_dir=PROJECT_ROOT)
        case "claude":
            return ClaudeExecutor(prompt_path=CLAUDE_PROMPT_FILE, working_dir=PROJECT_ROOT)
        case "codex":
            return CodexExecutor(config=config, working_dir=PROJECT_ROOT)
    raise ValueError(f"Unsupported tool requested: {tool}")


def run_ralph(tool: str, max_iterations: int) -> int:
    """Run the Ralph tool loop for a maximum number of iterations."""

    logger = configure_logging()

    try:
        config = _unwrap_result(load_config(), "Failed to load configuration")
    except RuntimeError as exc:
        log_error(logger, "Configuration error", exc)
        return 1

    log_info(
        logger,
        f"Configuration loaded: tool={tool} iterations={max_iterations} model={config.model}",
    )

    executor = _build_executor(tool, config)

    for iteration in range(1, max_iterations + 1):
        log_info(logger, "")
        log_info(logger, "=" * 63)
        log_info(logger, f"Ralph Iteration {iteration} of {max_iterations} ({tool})")
        log_info(logger, "=" * 63)

        try:
            output = _unwrap_result(executor.run(), "Tool execution failed")
        except RuntimeError as exc:
            log_error(logger, "Tool execution failed", exc)
            return 1

        if COMPLETE_MARKER in output:
            log_info(logger, "")
            log_success(logger, "Ralph completed all tasks!")
            log_success(logger, f"Completed at iteration {iteration} of {max_iterations}")
            return 0

        log_info(logger, f"Iteration {iteration} complete. Continuing...")
        time.sleep(2)

    log_info(logger, "")
    log_warning(
        logger,
        f"Ralph reached max iterations ({max_iterations}) without completing all tasks.",
    )
    return 1


__all__ = ["run_ralph"]
