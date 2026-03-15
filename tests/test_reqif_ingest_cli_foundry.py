"""Tests for the optional Foundry quality-eval adapter."""

from __future__ import annotations

from importlib.util import find_spec

import pytest
from returns.result import Failure, Success

from reqif_ingest_cli.foundry_adapter import (
    build_quality_eval_messages,
    create_foundry_chat_client,
    load_foundry_chat_config,
)
from reqif_ingest_cli.models import RequirementCandidate


def test_load_foundry_chat_config_requires_expected_env_keys() -> None:
    """Missing Foundry config should fail deterministically."""
    result = load_foundry_chat_config({})

    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, ValueError)
    assert "REQIF_INGEST_FOUNDRY_ENDPOINT" in str(error)


@pytest.mark.skipif(find_spec("azure.ai.inference") is None, reason="Install extra 'llm-review' for Foundry client tests.")
def test_load_foundry_chat_config_and_create_client() -> None:
    """Foundry client creation should not require a live network call."""
    result = load_foundry_chat_config(
        {
            "REQIF_INGEST_FOUNDRY_ENDPOINT": "https://example.test/models",
            "REQIF_INGEST_FOUNDRY_API_KEY": "test-api-key-1234",
            "REQIF_INGEST_FOUNDRY_MODEL": "gpt-4.1-mini",
        }
    )

    assert isinstance(result, Success)
    client_result = create_foundry_chat_client(result.unwrap())
    assert isinstance(client_result, Success)
    assert client_result.unwrap().__class__.__name__ == "ChatCompletionsClient"


def test_build_quality_eval_messages_keeps_candidates_read_only() -> None:
    """The evaluator prompt should describe review, not generation."""
    candidate = RequirementCandidate(
        schema="requirement_candidate/1",
        candidate_id="candidate-1",
        artifact_id="artifact-1",
        artifact_sha256="sha256-value",
        profile="aescsf_core_v2",
        key="ACCESS-1a",
        text="Identities are provisioned.",
        section="ACCESS-1",
        subtype_hints=[],
        extraction_rule_id="xlsx.aescsf_core.practice_row.v1",
        rationale="Mapped Practice ID and Practice columns from the AESCSF core workbook.",
        confidence_source="deterministic",
    )

    messages = build_quality_eval_messages([candidate])

    assert messages[0]["role"] == "system"
    assert "Do not invent new requirements" in messages[0]["content"]
    assert "ACCESS-1a" in messages[1]["content"]
