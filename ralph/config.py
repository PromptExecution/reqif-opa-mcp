"""Environment-backed configuration utilities for the Ralph CLI."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple, TypeAlias, cast

from returns.result import Failure, Result, Success


EnvMapping: TypeAlias = Mapping[str, str]
ReasoningEffort: TypeAlias = str

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_VALID_REASONING = {"low", "medium", "high"}


@dataclass(frozen=True, slots=True)
class RalphConfig:
    """Typed configuration values resolved from environment variables."""

    prompt_file: Path
    model: str
    reasoning_effort: ReasoningEffort
    sandbox: str
    full_auto: bool
    extra_args: Tuple[str, ...]


class ConfigurationError(ValueError):
    """Raised when configuration values are invalid."""


def _parse_bool(raw_value: str) -> Result[bool, ConfigurationError]:
    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return Success(True)
    if normalized in _FALSE_VALUES:
        return Success(False)
    msg = (
        "CODEX_FULL_AUTO must be one of: "
        f"{', '.join(sorted(_TRUE_VALUES | _FALSE_VALUES))}"
    )
    return Failure(ConfigurationError(msg))


def _parse_reasoning(raw_value: str) -> Result[ReasoningEffort, ConfigurationError]:
    normalized = raw_value.strip().lower()
    if normalized in _VALID_REASONING:
        return Success(cast(ReasoningEffort, normalized))
    msg = "CODEX_REASONING_EFFORT must be one of: low, medium, high"
    return Failure(ConfigurationError(msg))


def _parse_extra_args(value: str | None) -> Tuple[str, ...]:
    if value is None or not value.strip():
        return ()
    return tuple(shlex.split(value))


def _resolve_prompt_file(raw_value: str) -> Path:
    return Path(raw_value).expanduser().resolve()


def load_config(env: EnvMapping | None = None) -> Result[RalphConfig, ConfigurationError]:
    """Load Ralph configuration from environment variables with defaults."""

    source_env: EnvMapping = env if env is not None else os.environ

    prompt_path = _resolve_prompt_file(source_env.get("CODEX_PROMPT_FILE", "CLAUDE.md"))
    model = source_env.get("CODEX_MODEL", "gpt-5-codex")
    reasoning_raw = source_env.get("CODEX_REASONING_EFFORT", "high")
    sandbox = source_env.get("CODEX_SANDBOX", "workspace-write")
    full_auto_raw = source_env.get("CODEX_FULL_AUTO", "true")
    extra_args_raw = source_env.get("CODEX_EXTRA_ARGS")

    reasoning_result = _parse_reasoning(reasoning_raw)
    match reasoning_result:
        case Success(reasoning_effort):
            pass
        case Failure(error):
            return Failure(error)

    full_auto_result = _parse_bool(full_auto_raw)
    match full_auto_result:
        case Success(full_auto):
            pass
        case Failure(error):
            return Failure(error)

    config = RalphConfig(
        prompt_file=prompt_path,
        model=model,
        reasoning_effort=reasoning_effort,
        sandbox=sandbox,
        full_auto=full_auto,
        extra_args=_parse_extra_args(extra_args_raw),
    )
    return Success(config)


__all__ = [
    "ConfigurationError",
    "RalphConfig",
    "load_config",
]
