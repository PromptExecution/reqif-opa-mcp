"""Tool execution abstractions for the Ralph CLI."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Mapping, MutableMapping, Protocol, Sequence, cast

from returns.result import Failure, Result, Success

from ralph.config import RalphConfig
from ralph.logging_utils import configure_logging, log_error

Command = Sequence[str]


class ToolExecutor(Protocol):
    """Protocol defining Ralph tool executors."""

    def run(self) -> Result[str, Exception]:
        """Execute the tool and return aggregated output."""


@dataclass(frozen=True, slots=True)
class ExecutorError(RuntimeError):
    """Structured execution error for subprocess failures."""

    detail: str
    command: tuple[str, ...] | None = None
    returncode: int | None = None
    output: str = ""

    def __str__(self) -> str:  # pragma: no cover - trivial
        message = self.detail
        if self.command:
            message = f"{message} [{' '.join(self.command)}]"
        if self.returncode is not None:
            message = f"{message} (exit={self.returncode})"
        if self.output:
            snippet = self.output.strip()
            if snippet:
                message = f"{message}: {snippet}"
        return message


class _TeeToStderr(io.TextIOBase):
    """File-like tee that mirrors writes to sys.stderr and buffers output."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    def writable(self) -> bool:  # pragma: no cover - io.TextIOBase requirement
        return True

    def write(self, data: str) -> int:
        sys.stderr.write(data)
        sys.stderr.flush()
        self._parts.append(data)
        return len(data)

    def flush(self) -> None:  # pragma: no cover - delegated flush
        sys.stderr.flush()

    @property
    def value(self) -> str:
        return "".join(self._parts)


def _read_prompt(path: Path) -> Result[str, ExecutorError]:
    try:
        return Success(path.read_text(encoding="utf-8"))
    except OSError as exc:
        log_error(configure_logging(), f"Unable to read prompt file: {path}", exc)
        detail = f"Unable to read prompt file: {path}"
        return Failure(ExecutorError(detail=detail, output=str(exc)))


def _run_subprocess(
    command: Command,
    *,
    input_text: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Result[str, ExecutorError]:
    tee_stream = _TeeToStderr()
    stdout_stream: IO[str] = cast(IO[str], tee_stream)
    cwd_value = str(cwd) if cwd is not None else None
    env_value: MutableMapping[str, str] | None = None
    if env is not None:
        env_value = dict(env)
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            stdout=stdout_stream,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd_value,
            env=env_value,
            check=False,
        )
    except OSError as exc:
        log_error(configure_logging(), f"Failed to execute {' '.join(command)}", exc)
        detail = f"Failed to execute {' '.join(command)}"
        return Failure(ExecutorError(detail=detail, command=tuple(command), output=str(exc)))

    output = tee_stream.value
    if completed.returncode == 0:
        return Success(output)

    detail = f"Command {' '.join(command)} exited with {completed.returncode}"
    return Failure(
        ExecutorError(
            detail=detail,
            command=tuple(command),
            returncode=completed.returncode,
            output=output,
        )
    )


@dataclass(frozen=True, slots=True)
class AmpExecutor:
    """Executor for the amp CLI agent."""

    prompt_path: Path
    working_dir: Path | None = None

    def run(self) -> Result[str, Exception]:
        prompt_result = _read_prompt(self.prompt_path)
        match prompt_result:
            case Success(prompt_text):
                pass
            case Failure(error):
                return Failure(error)

        cwd_value = self.working_dir or self.prompt_path.parent
        command: Command = ("amp", "--dangerously-allow-all")
        return _run_subprocess(command, input_text=prompt_text, cwd=cwd_value)


@dataclass(frozen=True, slots=True)
class ClaudeExecutor:
    """Executor for Claude Code agent runs."""

    prompt_path: Path
    working_dir: Path | None = None

    def run(self) -> Result[str, Exception]:
        prompt_result = _read_prompt(self.prompt_path)
        match prompt_result:
            case Success(prompt_text):
                pass
            case Failure(error):
                return Failure(error)

        cwd_value = self.working_dir or self.prompt_path.parent
        command: Command = (
            "claude",
            "--model",
            "sonnet",
            "--dangerously-skip-permissions",
            "--print",
        )
        return _run_subprocess(command, input_text=prompt_text, cwd=cwd_value)


@dataclass(frozen=True, slots=True)
class CodexExecutor:
    """Executor for the Codex CLI with configuration-aware arguments."""

    config: RalphConfig
    working_dir: Path
    env: Mapping[str, str] | None = None

    def run(self) -> Result[str, Exception]:
        command: list[str] = [
            "codex",
            "exec",
            "-m",
            self.config.model,
            "--config",
            f'model_reasoning_effort="{self.config.reasoning_effort}"',
            "--sandbox",
            self.config.sandbox,
            "--dangerously-bypass-approvals-and-sandbox",
            "--cd",
            str(self.working_dir),
        ]

        if self.config.extra_args:
            command.extend(self.config.extra_args)

        command.append("@ralph-next")

        env_vars: MutableMapping[str, str]
        if self.env is not None:
            env_vars = dict(self.env)
        else:
            env_vars = dict(os.environ)

        env_vars.setdefault("CODEX_PROMPT_FILE", str(self.config.prompt_file))
        env_vars.setdefault("CODEX_MODEL", self.config.model)
        env_vars.setdefault("CODEX_REASONING_EFFORT", self.config.reasoning_effort)
        env_vars.setdefault("CODEX_SANDBOX", self.config.sandbox)
        env_vars.setdefault("CODEX_FULL_AUTO", "true" if self.config.full_auto else "false")
        if self.config.extra_args:
            env_vars.setdefault("CODEX_EXTRA_ARGS", " ".join(self.config.extra_args))

        return _run_subprocess(tuple(command), cwd=self.working_dir, env=env_vars)


__all__ = [
    "AmpExecutor",
    "ClaudeExecutor",
    "CodexExecutor",
    "ExecutorError",
    "ToolExecutor",
]
