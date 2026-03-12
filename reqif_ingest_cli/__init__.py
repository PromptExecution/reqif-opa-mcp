"""Standalone ingestion pipeline for deterministic document distillation."""

from reqif_ingest_cli.artifact import register_artifact
from reqif_ingest_cli.docling_adapter import (
    distill_docling_graph,
    extract_docling_document,
)
from reqif_ingest_cli.foundry_adapter import describe_foundry_config
from reqif_ingest_cli.reqif_emitter import emit_reqif_xml
from reqif_ingest_cli.xlsx_extractor import (
    distill_xlsx_requirements,
    extract_xlsx_document,
)

__all__ = [
    "describe_foundry_config",
    "distill_docling_graph",
    "distill_xlsx_requirements",
    "emit_reqif_xml",
    "extract_docling_document",
    "extract_xlsx_document",
    "register_artifact",
]
