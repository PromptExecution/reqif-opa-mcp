"""Small text and serialization helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HEADER_ALIASES: dict[str, str] = {
    "context and guidance": "context_guidance",
    "control": "requirement_text",
    "description": "requirement_text",
    "domain": "domain",
    "maturity indicator level": "mil",
    "mil": "mil",
    "objective": "objective",
    "objective id": "objective_id",
    "practice": "practice",
    "practice id": "practice_id",
    "requirement": "requirement_text",
    "requirement id": "requirement_id",
    "security profile": "security_profile",
    "self-evaluation notes": "self_evaluation_notes",
    "sp": "security_profile",
    "text": "requirement_text",
}
_MODAL_VERB_PATTERN = re.compile(
    r"\b(must|must not|shall|shall not|required to|should|should not)\b",
    re.IGNORECASE,
)


def utc_now_iso() -> str:
    """Return a UTC timestamp without fractional seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(value: object) -> str:
    """Normalize line endings and trim outer whitespace."""
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def collapse_whitespace(text: str) -> str:
    """Collapse internal whitespace to single spaces."""
    return " ".join(normalize_text(text).split())


def split_paragraphs(text: str) -> list[str]:
    """Split text into stable paragraph chunks."""
    raw = normalize_text(text)
    if not raw:
        return []
    parts = re.split(r"\n\s*\n+|\n(?=[*\-\u2022]\s)", raw)
    paragraphs: list[str] = []
    for part in parts:
        cleaned = re.sub(r"\s*\n\s*", " ", part.strip())
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def normalize_identifier(text: str) -> str:
    """Create an ASCII identifier fragment."""
    normalized = re.sub(r"[^a-z0-9]+", "_", collapse_whitespace(text).lower()).strip("_")
    return normalized or "value"


def stable_id(prefix: str, *parts: object, length: int = 12) -> str:
    """Create a stable identifier from semantic parts."""
    payload = "||".join(collapse_whitespace(str(part)) for part in parts if part is not None)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def column_name(index: int) -> str:
    """Convert a 1-based column number to spreadsheet notation."""
    current = index
    letters: list[str] = []
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def map_header_name(header: str, fallback_index: int) -> str:
    """Map a workbook header to a semantic identifier."""
    normalized = collapse_whitespace(header).lower()
    if not normalized:
        return f"column_{column_name(fallback_index).lower()}"
    return _HEADER_ALIASES.get(normalized, normalize_identifier(normalized))


def contains_modal_verb(text: str) -> bool:
    """Return whether a text span looks normatively relevant."""
    return bool(_MODAL_VERB_PATTERN.search(normalize_text(text)))


def to_jsonable(value: Any) -> Any:
    """Convert nested dataclasses and paths into JSON-ready values."""
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def json_dumps(value: Any, pretty: bool = False) -> str:
    """Dump a value as deterministic JSON."""
    return json.dumps(
        to_jsonable(value),
        indent=2 if pretty else None,
        sort_keys=True,
    )
