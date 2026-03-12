"""CLI entry point for the standalone ingestion pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from returns.result import Failure, Result

from reqif_ingest_cli.artifact import register_artifact
from reqif_ingest_cli.docling_adapter import distill_docling_graph, extract_docling_document
from reqif_ingest_cli.foundry_adapter import describe_foundry_config
from reqif_ingest_cli.models import RequirementCandidate
from reqif_ingest_cli.reqif_emitter import emit_reqif_xml, write_reqif_xml
from reqif_ingest_cli.utils import json_dumps
from reqif_ingest_cli.xlsx_extractor import distill_xlsx_requirements, extract_xlsx_document


def main() -> None:
    """Dispatch CLI commands."""
    parser = _build_parser()
    args = parser.parse_args()

    command = args.command
    if command == "register-artifact":
        _handle_json_result(
            register_artifact(
                args.path,
                source_uri=args.source_uri,
                document_profile=args.profile,
            ),
            pretty=args.pretty,
        )
        return

    if command == "extract":
        _handle_json_result(
            _extract_document(args.path, profile=args.profile, source_uri=args.source_uri),
            pretty=args.pretty,
        )
        return

    if command == "distill":
        _handle_json_result(
            _distill_document(args.path, profile=args.profile, source_uri=args.source_uri),
            pretty=args.pretty,
        )
        return

    if command == "emit-reqif":
        _emit_reqif_command(args)
        return

    if command == "foundry-config":
        print(json_dumps(describe_foundry_config(), pretty=args.pretty))
        return

    parser.print_help()
    sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Standalone ReqIF ingest CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    register = subparsers.add_parser("register-artifact", help="Register immutable artifact metadata")
    register.add_argument("path", help="Path to a local artifact")
    register.add_argument("--source-uri", help="Optional original source URI")
    register.add_argument("--profile", default=None, help="Optional document profile label")
    register.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    extract = subparsers.add_parser("extract", help="Extract a document graph from a source file")
    _add_document_args(extract)

    distill = subparsers.add_parser("distill", help="Distill requirement candidates from a source file")
    _add_document_args(distill)

    emit = subparsers.add_parser("emit-reqif", help="Emit ReqIF from a source file")
    _add_document_args(emit)
    emit.add_argument("--title", required=True, help="ReqIF baseline title")
    emit.add_argument("--comment", help="Optional ReqIF comment")
    emit.add_argument("--output", help="Optional output path for the ReqIF XML")

    foundry = subparsers.add_parser("foundry-config", help="Show optional Foundry evaluator status")
    foundry.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    return parser


def _add_document_args(parser: argparse.ArgumentParser) -> None:
    """Add shared document CLI arguments."""
    parser.add_argument("path", help="Path to a local document")
    parser.add_argument(
        "--profile",
        default="auto",
        help="Document profile override (default: auto)",
    )
    parser.add_argument("--source-uri", help="Optional original source URI")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")


def _extract_document(
    path: str,
    profile: str,
    source_uri: str | None,
) -> Result[Any, Exception]:
    """Dispatch extraction based on file extension."""
    suffix = Path(path).suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return extract_xlsx_document(path, source_uri=source_uri, profile=profile)
    return extract_docling_document(path, source_uri=source_uri, profile=profile)


def _distill_document(
    path: str,
    profile: str,
    source_uri: str | None,
) -> Result[list[RequirementCandidate], Exception]:
    """Dispatch distillation based on file extension."""
    suffix = Path(path).suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return distill_xlsx_requirements(path, source_uri=source_uri, profile=profile)

    graph_result = extract_docling_document(path, source_uri=source_uri, profile=profile)
    if isinstance(graph_result, Failure):
        return graph_result
    return _success(distill_docling_graph(graph_result.unwrap()))


def _emit_reqif_command(args: argparse.Namespace) -> None:
    """Emit ReqIF for a source document."""
    candidates_result = _distill_document(args.path, profile=args.profile, source_uri=args.source_uri)
    if isinstance(candidates_result, Failure):
        _fail(candidates_result.failure())
    candidates: list[RequirementCandidate] = candidates_result.unwrap()

    xml_result = emit_reqif_xml(candidates, title=args.title, comment=args.comment)
    if isinstance(xml_result, Failure):
        _fail(xml_result.failure())
    xml_text = xml_result.unwrap()

    if args.output:
        write_result = write_reqif_xml(args.output, xml_text)
        if isinstance(write_result, Failure):
            _fail(write_result.failure())
        print(
            json_dumps(
                {
                    "candidate_count": len(candidates),
                    "output_path": str(write_result.unwrap()),
                    "title": args.title,
                },
                pretty=args.pretty,
            )
        )
        return

    print(xml_text)


def _handle_json_result(result: Result[Any, Exception], pretty: bool) -> None:
    """Print a Result payload or exit on failure."""
    if isinstance(result, Failure):
        _fail(result.failure())
    print(json_dumps(result.unwrap(), pretty=pretty))


def _success(value: list[RequirementCandidate]) -> Result[list[RequirementCandidate], Exception]:
    """Wrap a value in a returns Result."""
    from returns.result import Success

    return Success(value)


def _fail(error: Exception) -> None:
    """Print a CLI error and exit."""
    print(f"error: {error}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
