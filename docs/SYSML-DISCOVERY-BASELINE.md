# SysML discovery baseline

Implements the ingestion portion of P0 from the root SysML discovery plan.

- ReqIF UID policy permits an original ReqIF identifier (schema description), so Unicode alphanumeric identifiers remain unchanged. The test now records exact identity expectations, including the deterministic UUID for a non-alphanumeric identifier.
- AESCSF core extraction sends physical column coordinates to paragraph creation, including repeated semantic headers. Reordered columns are tested against independent JSON fixtures; source anchors no longer guess a column from the count of content fields.
- Policy baseline values distinguish wrong scalar types from empty/whitespace strings.
- Foundry client tests skip at runtime if their optional Azure dependency is absent, leaving the rest of the module collectable.

Verification: locked uv dependencies, ingest-lite/nats-service/llm-review extras; full pytest suite, plus a separate environment without Azure. No live model calls are needed.
