"""Command-line interface for the Ralph automation tool."""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path
from typing import Sequence, cast

from returns.result import Failure, Success

from ralph.config import RalphConfig, load_config
from ralph.executors import AmpExecutor, ClaudeExecutor, CodexExecutor, ToolExecutor


VALID_TOOLS = ("amp", "claude", "codex")
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
PROMPT_FILE = PROJECT_ROOT / "prompt.md"
CLAUDE_PROMPT_FILE = PROJECT_ROOT / "CLAUDE.md"


def _positive_int(value: str) -> int:
    """Ensure provided iteration counts are positive integers."""

    try:
        numeric_value = int(value, 10)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise argparse.ArgumentTypeError("max_iterations must be an integer") from exc
    if numeric_value <= 0:
        msg = "max_iterations must be a positive integer"
        raise argparse.ArgumentTypeError(msg)
    return numeric_value


def _get_version() -> str:
    """Return installed project version, defaulting to dev marker."""

    try:
        return metadata.version("reqif-mcp")
    except metadata.PackageNotFoundError:
        return "0.0.0-dev"


class RalphCliArgs(argparse.Namespace):
    """Typed namespace wrapper for CLI arguments."""

    tool: str
    max_iterations: int


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for Ralph CLI."""

    parser = argparse.ArgumentParser(
        prog="ralph",
        description=(
            "Ralph automation harness. Execute supported tools with iterative control."
        ),
    )
    parser.add_argument(
        "--tool",
        choices=VALID_TOOLS,
        default="amp",
        help="Selects which automation tool to run (default: amp).",
    )
    parser.add_argument(
        "max_iterations",
        nargs="?",
        type=_positive_int,
        default=10,
        metavar="ITERATIONS",
        help="Maximum loop iterations (default: 10).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ralph %(prog)s {_get_version()}",
        help="Show version information and exit.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> RalphCliArgs:
    """Parse CLI arguments into a structured data object."""

    parser = build_parser()
    namespace = parser.parse_args(argv)
    return cast(RalphCliArgs, namespace)


def _build_executor(tool: str, config: RalphConfig) -> ToolExecutor:
    """Construct the executor for the requested tool."""

    match tool:
        case "amp":
            return AmpExecutor(prompt_path=PROMPT_FILE, working_dir=PROJECT_ROOT)
        case "claude":
            return ClaudeExecutor(prompt_path=CLAUDE_PROMPT_FILE, working_dir=PROJECT_ROOT)
        case "codex":
            return CodexExecutor(config=config, working_dir=PROJECT_ROOT)
    raise ValueError(f"Unsupported tool requested: {tool}")  # pragma: no cover - guarded by argparse


def run_cli(args: RalphCliArgs) -> int:
    """Load configuration and execute the selected tool."""

    config_result = load_config()
    match config_result:
        case Success(config):
            pass
        case Failure(error):  # pragma: no cover - defensive guard
            raise SystemExit(f"Configuration error: {error}")

    executor = _build_executor(args.tool, config)
    execution_result = executor.run()
    match execution_result:
        case Success(_):
            return 0
        case Failure(error):
            print(f"Tool execution failed: {error}", file=sys.stderr)
            return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint used by the uv script shim."""

    args = parse_args(argv)
    return run_cli(args)


if __name__ == "__main__":  # pragma: no cover - CLI guard
    raise SystemExit(main())
