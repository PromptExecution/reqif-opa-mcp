"""Command-line interface for the Ralph automation tool."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib import metadata
from typing import Sequence


VALID_TOOLS = ("amp", "claude", "codex")


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


@dataclass(frozen=True)
class RalphCliArgs:
    """Parsed CLI arguments."""

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
    return RalphCliArgs(tool=namespace.tool, max_iterations=namespace.max_iterations)


def run_cli(args: RalphCliArgs) -> int:
    """Placeholder runner that will invoke execution logic in future stories."""

    # Future stories will implement executor wiring; return success for now.
    _ = args
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint used by the uv script shim."""

    args = parse_args(argv)
    return run_cli(args)


if __name__ == "__main__":  # pragma: no cover - CLI guard
    raise SystemExit(main())
