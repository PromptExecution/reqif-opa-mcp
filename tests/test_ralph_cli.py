"""Tests for Ralph CLI and supporting modules."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import pytest
from returns.maybe import Some
from returns.result import Failure, Success

from ralph import archiver, file_manager
from ralph.config import RalphConfig, load_config
from ralph.executors import AmpExecutor, CodexExecutor
from ralph.ralph_cli import parse_args


class FixedDate(date):
    """Fixed date helper for archival tests."""

    @classmethod
    def today(cls) -> "FixedDate":
        return cls(2026, 1, 31)


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.tool == "amp"
    assert args.max_iterations == 10


def test_parse_args_custom() -> None:
    args = parse_args(["--tool", "codex", "5"])
    assert args.tool == "codex"
    assert args.max_iterations == 5


def test_parse_args_rejects_zero_iterations() -> None:
    with pytest.raises(SystemExit):
        parse_args(["0"])


def test_load_config_from_env(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hello", encoding="utf-8")
    env: Mapping[str, str] = {
        "CODEX_PROMPT_FILE": str(prompt_file),
        "CODEX_MODEL": "gpt-5-codex",
        "CODEX_REASONING_EFFORT": "medium",
        "CODEX_SANDBOX": "workspace-write",
        "CODEX_FULL_AUTO": "false",
        "CODEX_EXTRA_ARGS": "--foo bar",
    }
    result = load_config(env)
    assert isinstance(result, Success)
    config = result.unwrap()
    assert config.prompt_file == prompt_file.resolve()
    assert config.model == "gpt-5-codex"
    assert config.reasoning_effort == "medium"
    assert config.sandbox == "workspace-write"
    assert config.full_auto is False
    assert config.extra_args == ("--foo", "bar")


def test_load_config_invalid_reasoning() -> None:
    env: Mapping[str, str] = {"CODEX_REASONING_EFFORT": "invalid"}
    result = load_config(env)
    assert isinstance(result, Failure)


def _fake_run_factory(record: dict[str, Any], returncode: int = 0):
    def _fake_run(
        command,
        *,
        input=None,
        stdout=None,
        stderr=None,
        text=None,
        cwd=None,
        env=None,
        check=None,
    ):
        record["command"] = command
        record["input"] = input
        record["cwd"] = cwd
        record["env"] = env
        if stdout is not None:
            stdout.write("ok\n")
        class _Result:
            pass
        result = _Result()
        result.returncode = returncode
        return result

    return _fake_run


def test_amp_executor_runs_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("prompt", encoding="utf-8")
    record: dict[str, Any] = {}
    monkeypatch.setattr(
        "ralph.executors.subprocess.run",
        _fake_run_factory(record),
    )

    executor = AmpExecutor(prompt_path=prompt_file, working_dir=tmp_path)
    result = executor.run()
    assert isinstance(result, Success)
    assert "ok" in result.unwrap()
    assert record["command"] == ("amp", "--dangerously-allow-all")


def test_codex_executor_builds_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_file = tmp_path / "CLAUDE.md"
    prompt_file.write_text("prompt", encoding="utf-8")
    record: dict[str, Any] = {}
    monkeypatch.setattr(
        "ralph.executors.subprocess.run",
        _fake_run_factory(record),
    )

    config = RalphConfig(
        prompt_file=prompt_file,
        model="gpt-5-codex",
        reasoning_effort="high",
        sandbox="workspace-write",
        full_auto=True,
        extra_args=("--foo", "bar"),
    )
    executor = CodexExecutor(config=config, working_dir=tmp_path)
    result = executor.run()
    assert isinstance(result, Success)
    command = list(record["command"])
    assert command[:3] == ["codex", "exec", "-m"]
    assert "--foo" in command
    assert record["env"]["CODEX_MODEL"] == "gpt-5-codex"


def test_executor_handles_subprocess_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("prompt", encoding="utf-8")

    def _raise(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("ralph.executors.subprocess.run", _raise)

    executor = AmpExecutor(prompt_path=prompt_file, working_dir=tmp_path)
    result = executor.run()
    assert isinstance(result, Failure)


def test_file_manager_reads_prd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prd_path = tmp_path / "prd.json"
    progress_path = tmp_path / "progress.txt"
    prd_path.write_text(json.dumps({"branchName": "feature/test"}), encoding="utf-8")

    monkeypatch.setattr(file_manager, "PRD_PATH", prd_path)
    monkeypatch.setattr(file_manager, "PROGRESS_PATH", progress_path)

    result = file_manager.read_prd()
    assert isinstance(result, Success)

    branch = file_manager.get_current_branch()
    match branch:
        case Some(value):
            assert value == "feature/test"
        case _:
            pytest.fail("Expected branchName to be read")

    append_result = file_manager.append_to_progress("hello")
    assert isinstance(append_result, Success)
    assert progress_path.read_text(encoding="utf-8") == "hello\n"


def test_archiver_detects_branch_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prd_path = tmp_path / "prd.json"
    progress_path = tmp_path / "progress.txt"
    archive_dir = tmp_path / "archive"
    last_branch_path = tmp_path / ".last-branch"

    prd_path.write_text(json.dumps({"branchName": "ralph/new-branch"}), encoding="utf-8")
    progress_path.write_text("progress", encoding="utf-8")
    last_branch_path.write_text("ralph/old-branch", encoding="utf-8")

    monkeypatch.setattr(file_manager, "PRD_PATH", prd_path)
    monkeypatch.setattr(file_manager, "PROGRESS_PATH", progress_path)
    monkeypatch.setattr(archiver, "PRD_PATH", prd_path)
    monkeypatch.setattr(archiver, "PROGRESS_PATH", progress_path)
    monkeypatch.setattr(archiver, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(archiver, "LAST_BRANCH_PATH", last_branch_path)
    monkeypatch.setattr(archiver, "date", FixedDate)

    changed = archiver.check_branch_change()
    assert changed is True

    archive_folder = archive_dir / "2026-01-31-old-branch"
    assert (archive_folder / "prd.json").read_text(encoding="utf-8")
    assert (archive_folder / "progress.txt").read_text(encoding="utf-8") == "progress"
    assert progress_path.read_text(encoding="utf-8") == ""
    assert last_branch_path.read_text(encoding="utf-8") == "ralph/new-branch"


def test_archiver_initializes_last_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prd_path = tmp_path / "prd.json"
    progress_path = tmp_path / "progress.txt"
    archive_dir = tmp_path / "archive"
    last_branch_path = tmp_path / ".last-branch"

    prd_path.write_text(json.dumps({"branchName": "ralph/start"}), encoding="utf-8")

    monkeypatch.setattr(file_manager, "PRD_PATH", prd_path)
    monkeypatch.setattr(file_manager, "PROGRESS_PATH", progress_path)
    monkeypatch.setattr(archiver, "PRD_PATH", prd_path)
    monkeypatch.setattr(archiver, "PROGRESS_PATH", progress_path)
    monkeypatch.setattr(archiver, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(archiver, "LAST_BRANCH_PATH", last_branch_path)

    changed = archiver.check_branch_change()
    assert changed is False
    assert last_branch_path.read_text(encoding="utf-8") == "ralph/start"
