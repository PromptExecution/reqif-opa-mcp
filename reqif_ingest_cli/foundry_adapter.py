"""Optional Azure Foundry adapter for gated quality evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Any, Mapping, Sequence

from returns.result import Failure, Result, Success

from reqif_ingest_cli.models import RequirementCandidate


@dataclass(slots=True)
class FoundryChatConfig:
    """Configuration for Azure Foundry chat completions."""

    endpoint: str
    api_key: str
    model: str
    api_version: str = "2024-05-01-preview"


def load_foundry_chat_config(
    env: Mapping[str, str] | None = None,
) -> Result[FoundryChatConfig, Exception]:
    """Load config from environment variables."""
    values = env or environ
    endpoint = values.get("REQIF_INGEST_FOUNDRY_ENDPOINT", "")
    api_key = values.get("REQIF_INGEST_FOUNDRY_API_KEY", "")
    model = values.get("REQIF_INGEST_FOUNDRY_MODEL", "")

    missing = [
        name
        for name, value in {
            "REQIF_INGEST_FOUNDRY_ENDPOINT": endpoint,
            "REQIF_INGEST_FOUNDRY_API_KEY": api_key,
            "REQIF_INGEST_FOUNDRY_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        return Failure(ValueError(f"Missing Foundry configuration: {', '.join(missing)}"))

    return Success(
        FoundryChatConfig(
            endpoint=endpoint,
            api_key=api_key,
            model=model,
        )
    )


def create_foundry_chat_client(config: FoundryChatConfig) -> Result[Any, Exception]:
    """Create an Azure Foundry chat client without making network calls."""
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential

        client = ChatCompletionsClient(
            endpoint=config.endpoint,
            credential=AzureKeyCredential(config.api_key),
            api_version=config.api_version,
        )
        return Success(client)
    except Exception as exc:
        return Failure(exc)


def build_quality_eval_messages(
    candidates: Sequence[RequirementCandidate],
) -> list[dict[str, str]]:
    """Create a deterministic evaluator prompt envelope."""
    bullet_lines = [
        f"- {candidate.key}: {candidate.text}"
        for candidate in candidates
    ]
    return [
        {
            "role": "system",
            "content": (
                "You review deterministic requirement candidates. "
                "Do not invent new requirements. Flag only mapping or coverage issues."
            ),
        },
        {
            "role": "user",
            "content": "\n".join(
                [
                    "Review these derived requirement candidates for quality issues:",
                    *bullet_lines,
                ]
            ),
        },
    ]


def describe_foundry_config(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return a JSON-ready status document for the optional LLM boundary."""
    config_result = load_foundry_chat_config(env)
    if isinstance(config_result, Failure):
        return {
            "configured": False,
            "provider": "azure_foundry",
            "error": str(config_result.failure()),
        }

    config = config_result.unwrap()
    return {
        "configured": True,
        "provider": "azure_foundry",
        "endpoint": config.endpoint,
        "model": config.model,
        "api_version": config.api_version,
        "api_key_masked": _mask_secret(config.api_key),
    }


def _mask_secret(secret: str) -> str:
    """Mask an API key for display."""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"
