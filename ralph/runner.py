"""Iteration runner for Ralph automation."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from returns.result import Failure

from ralph.config import RalphConfig, load_config
from ralph.executors import AmpExecutor, ClaudeExecutor, CodexExecutor, ToolExecutor

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
PROMPT_FILE = PROJECT_ROOT / "prompt.md"
CLAUDE_PROMPT_FILE = PROJECT_ROOT / "CLAUDE.md"
COMPLETE_MARKER = "<promise>COMPLETE</promise>"


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

    config_result = load_config()
    if isinstance(config_result, Failure):
        error = config_result.failure()
        print(f"Configuration error: {error}", file=sys.stderr)
        return 1
    config = config_result.unwrap()

    executor = _build_executor(tool, config)

    for iteration in range(1, max_iterations + 1):
        print("")
        print("=" * 63)
        print(f"  Ralph Iteration {iteration} of {max_iterations} ({tool})")
        print("=" * 63)

        result = executor.run()
        if isinstance(result, Failure):
            error = result.failure()
            print(f"Tool execution failed: {error}", file=sys.stderr)
            return 1

        output = result.unwrap()
        if COMPLETE_MARKER in output:
            print("")
            print("Ralph completed all tasks!")
            print(f"Completed at iteration {iteration} of {max_iterations}")
            return 0

        print(f"Iteration {iteration} complete. Continuing...")
        time.sleep(2)

    print("")
    print(f"Ralph reached max iterations ({max_iterations}) without completing all tasks.")
    return 1


__all__ = ["run_ralph"]
