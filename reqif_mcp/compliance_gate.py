"""Compliance gate orchestration with explicit meta-policy checks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, cast

from returns.result import Failure
from ulid import ULID

from reqif_mcp.normalization import normalize_reqif
from reqif_mcp.opa_evaluator import evaluate_requirement, load_bundle_manifest
from reqif_mcp.reqif_parser import parse_reqif_xml
from reqif_mcp.sarif_producer import generate_sarif_report, write_sarif_file
from reqif_mcp.server import reqif_write_verification


@dataclass(slots=True)
class GateIssue:
    """Structured error or warning surfaced by the compliance gate."""

    code: str
    stage: str
    message: str
    severity: str = "error"
    requirement_uid: str | None = None
    requirement_key: str | None = None


@dataclass(slots=True)
class GateResult:
    """Successful evaluation row."""

    requirement_uid: str
    requirement_key: str
    severity: str
    status: str
    score: float
    evaluation_id: str
    sarif_path: str


@dataclass(slots=True)
class GateSummary:
    """High-level gate summary persisted for CI diagnostics."""

    gate_status: str
    subtype: str
    baseline_requirement_count: int
    selected_requirement_count: int
    attempted_evaluations: int
    successful_evaluations: int
    verification_events_written: int
    applied_filters: list[str] = field(default_factory=list)
    result_counts: dict[str, int] = field(default_factory=dict)
    meta_policy_failure_count: int = 0
    processing_failure_count: int = 0
    gate_failure_count: int = 0
    meta_policy_failures: list[GateIssue] = field(default_factory=list)
    processing_failures: list[GateIssue] = field(default_factory=list)
    gate_failures: list[GateIssue] = field(default_factory=list)


def main() -> None:
    """CLI entry point for the CI compliance gate."""
    parser = _build_parser()
    args = parser.parse_args()
    exit_code = run_compliance_gate(
        reqif_path=Path(args.reqif_path),
        facts_path=Path(args.facts_path),
        bundle_path=Path(args.bundle_path),
        subtype=args.subtype,
        package=args.package,
        requirement_keys=args.requirement_key,
        attribute_filters=args.attribute_filter,
        text_filters=args.text_contains,
        limit=args.limit,
        baseline_id=args.baseline_id,
        baseline_version=args.baseline_version,
        out_dir=Path(args.out_dir),
    )
    raise SystemExit(exit_code)


def _build_parser() -> argparse.ArgumentParser:
    """Build the compliance gate CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run the compliance gate with explicit meta-policy checks.",
    )
    parser.add_argument("--reqif-path", required=True, help="ReqIF baseline XML path")
    parser.add_argument("--facts-path", required=True, help="Agent facts JSON path")
    parser.add_argument("--bundle-path", required=True, help="OPA bundle directory")
    parser.add_argument("--subtype", required=True, help="Subtype to evaluate")
    parser.add_argument("--package", help="OPA package override")
    parser.add_argument(
        "--requirement-key",
        action="append",
        default=[],
        help="Repeatable exact requirement key filter applied after subtype selection.",
    )
    parser.add_argument(
        "--attribute-filter",
        action="append",
        default=[],
        help="Repeatable filter in the form name=value or attrs.name=value.",
    )
    parser.add_argument(
        "--text-contains",
        action="append",
        default=[],
        help="Repeatable case-insensitive substring filter applied to requirement text.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of requirements to evaluate after filtering.",
    )
    parser.add_argument("--baseline-id", default="CI-BASELINE-2024")
    parser.add_argument("--baseline-version", default="1.0.0")
    parser.add_argument("--out-dir", default=".")
    return parser


def run_compliance_gate(
    reqif_path: Path,
    facts_path: Path,
    bundle_path: Path,
    subtype: str,
    package: str | None,
    requirement_keys: list[str] | None,
    attribute_filters: list[str] | None,
    text_filters: list[str] | None,
    limit: int | None,
    baseline_id: str,
    baseline_version: str,
    out_dir: Path,
) -> int:
    """Execute the compliance gate and persist diagnostic artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        return _run_compliance_gate(
            reqif_path=reqif_path,
            facts_path=facts_path,
            bundle_path=bundle_path,
            subtype=subtype,
            package=package,
            requirement_keys=requirement_keys,
            attribute_filters=attribute_filters,
            text_filters=text_filters,
            limit=limit,
            baseline_id=baseline_id,
            baseline_version=baseline_version,
            out_dir=out_dir,
        )
    except Exception as exc:
        issue = GateIssue(
            code="UNHANDLED_GATE_EXCEPTION",
            stage="gate",
            message=f"{type(exc).__name__}: {exc}",
        )
        summary = GateSummary(
            gate_status="failed_processing",
            subtype=subtype,
            baseline_requirement_count=0,
            selected_requirement_count=0,
            attempted_evaluations=0,
            successful_evaluations=0,
            verification_events_written=0,
            applied_filters=_describe_filters(
                requirement_keys=requirement_keys or [],
                attribute_filters=attribute_filters or [],
                text_filters=text_filters or [],
                limit=limit,
            ),
            processing_failure_count=1,
            processing_failures=[issue],
        )
        _persist_outputs(out_dir=out_dir, results=[], summary=summary)
        _print_summary(summary)
        return 3


def _run_compliance_gate(
    reqif_path: Path,
    facts_path: Path,
    bundle_path: Path,
    subtype: str,
    package: str | None,
    requirement_keys: list[str] | None,
    attribute_filters: list[str] | None,
    text_filters: list[str] | None,
    limit: int | None,
    baseline_id: str,
    baseline_version: str,
    out_dir: Path,
) -> int:
    """Core compliance gate execution path."""

    meta_policy_failures: list[GateIssue] = []
    processing_failures: list[GateIssue] = []
    gate_failures: list[GateIssue] = []
    results: list[GateResult] = []
    verification_events_written = 0

    requirements = _load_requirements(
        reqif_path=reqif_path,
        baseline_id=baseline_id,
        baseline_version=baseline_version,
        meta_policy_failures=meta_policy_failures,
    )
    facts = _load_facts(facts_path, meta_policy_failures)
    bundle_manifest = _load_bundle(bundle_path, meta_policy_failures)

    _write_json(out_dir / "baseline_requirements.json", requirements)

    subtype_requirements = _select_requirements(requirements, subtype)
    selected_requirements = _apply_requirement_filters(
        requirements=subtype_requirements,
        requirement_keys=requirement_keys or [],
        attribute_filters=attribute_filters or [],
        text_filters=text_filters or [],
        limit=limit,
    )
    _write_json(out_dir / "requirements.json", selected_requirements)

    meta_policy_failures.extend(
        _validate_meta_policies(
            reqif_path=reqif_path,
            subtype=subtype,
            package=package,
            bundle_manifest=bundle_manifest,
            requirements=requirements,
            subtype_requirements=subtype_requirements,
            selected_requirements=selected_requirements,
            facts=facts,
            filters_applied=bool((requirement_keys or []) or (attribute_filters or []) or (text_filters or []) or limit),
        )
    )

    attempted_evaluations = 0
    if not meta_policy_failures:
        for requirement in selected_requirements:
            attempted_evaluations += 1
            evaluation_id = str(ULID())
            results_or_issue = _evaluate_one_requirement(
                requirement=requirement,
                facts=facts,
                bundle_path=bundle_path,
                package=package,
                evaluation_id=evaluation_id,
                out_dir=out_dir,
            )
            if isinstance(results_or_issue, GateIssue):
                processing_failures.append(results_or_issue)
                continue

            results.append(results_or_issue)
            verification_issue = _write_verification_event(
                result=results_or_issue,
                facts=facts,
            )
            if verification_issue is None:
                verification_events_written += 1
            else:
                processing_failures.append(verification_issue)

    if selected_requirements and not results:
        processing_failures.append(
            GateIssue(
                code="ZERO_SUCCESSFUL_EVALUATIONS",
                stage="evaluation",
                message=(
                    "Selected requirements were present, but zero evaluations produced usable results. "
                    "Treating this as a hard compliance gate failure."
                ),
            )
        )

    gate_failures.extend(_derive_gate_failures(results))

    summary = GateSummary(
        gate_status=_gate_status(meta_policy_failures, processing_failures, gate_failures),
        subtype=subtype,
        baseline_requirement_count=len(requirements),
        selected_requirement_count=len(selected_requirements),
        attempted_evaluations=attempted_evaluations,
        successful_evaluations=len(results),
        verification_events_written=verification_events_written,
        applied_filters=_describe_filters(
            requirement_keys=requirement_keys or [],
            attribute_filters=attribute_filters or [],
            text_filters=text_filters or [],
            limit=limit,
        ),
        result_counts=dict(Counter(result.status for result in results)),
        meta_policy_failure_count=len(meta_policy_failures),
        processing_failure_count=len(processing_failures),
        gate_failure_count=len(gate_failures),
        meta_policy_failures=meta_policy_failures,
        processing_failures=processing_failures,
        gate_failures=gate_failures,
    )

    _persist_outputs(out_dir=out_dir, results=results, summary=summary)
    _print_summary(summary)

    if summary.gate_status == "failed_meta_policy":
        return 2
    if summary.gate_status == "failed_processing":
        return 3
    if summary.gate_status == "failed_gate":
        return 4
    return 0


def _load_requirements(
    reqif_path: Path,
    baseline_id: str,
    baseline_version: str,
    meta_policy_failures: list[GateIssue],
) -> list[dict[str, Any]]:
    """Load and normalize requirements from a ReqIF baseline."""
    if not reqif_path.exists():
        meta_policy_failures.append(
            GateIssue(
                code="REQIF_NOT_FOUND",
                stage="load_reqif",
                message=f"ReqIF baseline file does not exist: {reqif_path}",
            )
        )
        return []

    parse_result = parse_reqif_xml(reqif_path)
    if isinstance(parse_result, Failure):
        meta_policy_failures.append(
            GateIssue(
                code="REQIF_PARSE_FAILED",
                stage="load_reqif",
                message=str(parse_result.failure()),
            )
        )
        return []

    normalize_result = normalize_reqif(
        parse_result.unwrap(),
        policy_baseline_id=baseline_id,
        policy_baseline_version=baseline_version,
    )
    if isinstance(normalize_result, Failure):
        meta_policy_failures.append(
            GateIssue(
                code="REQIF_NORMALIZE_FAILED",
                stage="normalize_reqif",
                message=str(normalize_result.failure()),
            )
        )
        return []

    return normalize_result.unwrap()


def _load_facts(
    facts_path: Path,
    meta_policy_failures: list[GateIssue],
) -> dict[str, Any]:
    """Load agent facts JSON."""
    if not facts_path.exists():
        meta_policy_failures.append(
            GateIssue(
                code="FACTS_NOT_FOUND",
                stage="load_facts",
                message=f"Agent facts file does not exist: {facts_path}",
            )
        )
        return {}

    try:
        return json.loads(facts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        meta_policy_failures.append(
            GateIssue(
                code="FACTS_INVALID_JSON",
                stage="load_facts",
                message=f"Agent facts JSON is invalid: {exc}",
            )
        )
        return {}


def _load_bundle(
    bundle_path: Path,
    meta_policy_failures: list[GateIssue],
) -> dict[str, Any]:
    """Load bundle manifest for meta-policy validation."""
    manifest_result = load_bundle_manifest(bundle_path)
    if isinstance(manifest_result, Failure):
        meta_policy_failures.append(
            GateIssue(
                code="BUNDLE_MANIFEST_FAILED",
                stage="load_bundle",
                message=str(manifest_result.failure()),
            )
        )
        return {}
    return manifest_result.unwrap()


def _select_requirements(
    requirements: list[dict[str, Any]],
    subtype: str,
) -> list[dict[str, Any]]:
    """Select active requirements matching the requested subtype."""
    return [
        requirement
        for requirement in requirements
        if subtype in requirement.get("subtypes", []) and requirement.get("status") == "active"
    ]


def _apply_requirement_filters(
    requirements: list[dict[str, Any]],
    requirement_keys: list[str],
    attribute_filters: list[str],
    text_filters: list[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    """Apply deterministic post-selection filters to requirements."""
    normalized_keys = {value.strip() for value in requirement_keys if value.strip()}
    parsed_attribute_filters = [_parse_attribute_filter(value) for value in attribute_filters if value.strip()]
    normalized_text_filters = [value.strip().lower() for value in text_filters if value.strip()]

    filtered: list[dict[str, Any]] = []
    for requirement in requirements:
        if normalized_keys and str(requirement.get("key", "")) not in normalized_keys:
            continue
        if parsed_attribute_filters and not all(
            _requirement_attribute_matches(requirement, path, expected)
            for path, expected in parsed_attribute_filters
        ):
            continue
        if normalized_text_filters:
            requirement_text = str(requirement.get("text", "")).lower()
            if not all(fragment in requirement_text for fragment in normalized_text_filters):
                continue
        filtered.append(requirement)

    if limit is not None:
        return filtered[:limit]
    return filtered


def _parse_attribute_filter(raw_filter: str) -> tuple[str, str]:
    """Parse an attribute filter expression."""
    if "=" not in raw_filter:
        raise ValueError(f"Invalid attribute filter {raw_filter!r}; expected name=value")
    name, value = raw_filter.split("=", 1)
    parsed_name = name.strip()
    parsed_value = value.strip()
    if not parsed_name or not parsed_value:
        raise ValueError(f"Invalid attribute filter {raw_filter!r}; expected name=value")
    return parsed_name, parsed_value


def _requirement_attribute_matches(
    requirement: dict[str, Any],
    path: str,
    expected: str,
) -> bool:
    """Match a dotted requirement or attrs path against an expected string value."""
    parts = path.split(".")
    current: Any = requirement
    for index, part in enumerate(parts):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if index == 0 and "attrs" in requirement and isinstance(requirement.get("attrs"), dict):
            current = requirement["attrs"]
            if part in current:
                current = current[part]
                continue
        return False
    return str(current) == expected


def _describe_filters(
    requirement_keys: list[str],
    attribute_filters: list[str],
    text_filters: list[str],
    limit: int | None,
) -> list[str]:
    """Render applied filters for summaries and diagnostics."""
    description: list[str] = []
    if requirement_keys:
        description.append(f"requirement_key in {sorted({value for value in requirement_keys if value})}")
    for attr_filter in attribute_filters:
        if attr_filter:
            description.append(f"attribute {attr_filter}")
    for text_filter in text_filters:
        if text_filter:
            description.append(f"text contains {text_filter!r}")
    if limit is not None:
        description.append(f"limit={limit}")
    return description


def _validate_meta_policies(
    reqif_path: Path,
    subtype: str,
    package: str | None,
    bundle_manifest: dict[str, Any],
    requirements: list[dict[str, Any]],
    subtype_requirements: list[dict[str, Any]],
    selected_requirements: list[dict[str, Any]],
    facts: dict[str, Any],
    filters_applied: bool,
) -> list[GateIssue]:
    """Validate meta-policy controls before evaluation."""
    issues: list[GateIssue] = []

    if not requirements:
        issues.append(
            GateIssue(
                code="EMPTY_BASELINE",
                stage="meta_policy",
                message=(
                    f"Normalized ReqIF baseline from {reqif_path} contains zero requirements. "
                    "A policy baseline must contain at least one requirement."
                ),
            )
        )

    if not subtype_requirements:
        issues.append(
            GateIssue(
                code="EMPTY_SELECTION",
                stage="meta_policy",
                message=(
                    f"No active requirements matched subtype {subtype}. "
                    "A compliance evaluation must select at least one requirement."
                ),
            )
        )
    elif not selected_requirements and filters_applied:
        issues.append(
            GateIssue(
                code="EMPTY_FILTERED_SELECTION",
                stage="meta_policy",
                message=(
                    f"Subtype {subtype} matched active requirements, but the additional filters reduced the "
                    "evaluation set to zero."
                ),
            )
        )

    if not facts:
        issues.append(
            GateIssue(
                code="EMPTY_FACTS",
                stage="meta_policy",
                message="Agent facts were empty or failed to load.",
            )
        )
    else:
        for key in ("target", "facts", "evidence", "agent"):
            if key not in facts:
                issues.append(
                    GateIssue(
                        code="FACTS_SCHEMA_INCOMPLETE",
                        stage="meta_policy",
                        message=f"Agent facts are missing required top-level field: {key}",
                    )
                )

        if not facts.get("evidence"):
            issues.append(
                GateIssue(
                    code="EMPTY_EVIDENCE",
                    stage="meta_policy",
                    message="Agent facts must include at least one evidence item.",
                )
            )

        target = facts.get("target", {})
        for key in ("repo", "commit", "build"):
            if not target.get(key):
                issues.append(
                    GateIssue(
                        code="TARGET_METADATA_INCOMPLETE",
                        stage="meta_policy",
                        message=f"Agent target metadata is missing required field: {key}",
                    )
                )

        agent = facts.get("agent", {})
        for key in ("name", "version"):
            if not agent.get(key):
                issues.append(
                    GateIssue(
                        code="AGENT_METADATA_INCOMPLETE",
                        stage="meta_policy",
                        message=f"Agent metadata is missing required field: {key}",
                    )
                )

        for index, evidence in enumerate(facts.get("evidence", [])):
            if not evidence.get("type") or not evidence.get("uri"):
                issues.append(
                    GateIssue(
                        code="EVIDENCE_SCHEMA_INCOMPLETE",
                        stage="meta_policy",
                        message=(
                            "Evidence items must include both type and uri. "
                            f"Found incomplete evidence at index {index}."
                        ),
                    )
                )

    manifest_subtypes = bundle_manifest.get("metadata", {}).get("subtypes", [])
    if manifest_subtypes and subtype not in manifest_subtypes:
        issues.append(
            GateIssue(
                code="BUNDLE_SUBTYPE_MISMATCH",
                stage="meta_policy",
                message=(
                    f"Bundle manifest declares subtypes {manifest_subtypes}, which does not include requested subtype {subtype}."
                ),
            )
        )

    manifest_roots = bundle_manifest.get("roots", [])
    if package is not None:
        package_root = package.split(".", 1)[0]
        if manifest_roots and package_root not in manifest_roots:
            issues.append(
                GateIssue(
                    code="PACKAGE_ROOT_MISMATCH",
                    stage="meta_policy",
                    message=(
                        f"OPA package {package} does not align with bundle roots {manifest_roots}."
                    ),
                )
            )

    duplicate_uids = _find_duplicates(str(requirement.get("uid", "")) for requirement in requirements)
    for duplicate_uid in duplicate_uids:
        issues.append(
            GateIssue(
                code="DUPLICATE_REQUIREMENT_UID",
                stage="meta_policy",
                message=f"Normalized baseline contains duplicate requirement uid {duplicate_uid}.",
                requirement_uid=duplicate_uid,
            )
        )

    duplicate_keys = _find_duplicates(str(requirement.get("key", "")) for requirement in requirements)
    for duplicate_key in duplicate_keys:
        issues.append(
            GateIssue(
                code="DUPLICATE_REQUIREMENT_KEY",
                stage="meta_policy",
                message=f"Normalized baseline contains duplicate requirement key {duplicate_key}.",
                requirement_key=duplicate_key,
            )
        )

    for requirement in selected_requirements:
        if not str(requirement.get("text", "")).strip():
            issues.append(
                GateIssue(
                    code="EMPTY_REQUIREMENT_TEXT",
                    stage="meta_policy",
                    message="Selected requirement has empty text.",
                    requirement_uid=str(requirement.get("uid", "")),
                    requirement_key=str(requirement.get("key", "")),
                )
            )
        if package is None and not requirement.get("rubrics"):
            issues.append(
                GateIssue(
                    code="MISSING_REQUIREMENT_RUBRICS",
                    stage="meta_policy",
                    message="Selected requirement has no rubrics and no package override was supplied.",
                    requirement_uid=str(requirement.get("uid", "")),
                    requirement_key=str(requirement.get("key", "")),
                )
            )

    return issues


def _evaluate_one_requirement(
    requirement: dict[str, Any],
    facts: dict[str, Any],
    bundle_path: Path,
    package: str | None,
    evaluation_id: str,
    out_dir: Path,
) -> GateResult | GateIssue:
    """Evaluate one requirement and persist its SARIF."""
    eval_result = evaluate_requirement(
        requirement=requirement,
        facts=facts,
        bundle_path=str(bundle_path),
        package=package,
        context={"target": facts.get("target", {})},
        enable_decision_logging=True,
    )
    if isinstance(eval_result, Failure):
        return GateIssue(
            code="OPA_EVALUATION_FAILED",
            stage="evaluate",
            message=str(eval_result.failure()),
            requirement_uid=str(requirement.get("uid", "")),
            requirement_key=str(requirement.get("key", "")),
        )

    try:
        decision = eval_result.unwrap()
        sarif_report = generate_sarif_report(requirement, decision, facts, evaluation_id)
    except Exception as exc:
        return GateIssue(
            code="SARIF_GENERATION_FAILED",
            stage="sarif",
            message=str(exc),
            requirement_uid=str(requirement.get("uid", "")),
            requirement_key=str(requirement.get("key", "")),
        )

    sarif_path = out_dir / "evidence_store" / "sarif" / f"{evaluation_id}.sarif"
    write_result = write_sarif_file(sarif_report, sarif_path)
    if isinstance(write_result, Failure):
        return GateIssue(
            code="SARIF_WRITE_FAILED",
            stage="sarif",
            message=str(write_result.failure()),
            requirement_uid=str(requirement.get("uid", "")),
            requirement_key=str(requirement.get("key", "")),
        )

    return GateResult(
        requirement_uid=str(requirement.get("uid", "")),
        requirement_key=str(requirement.get("key", "")),
        severity=str(requirement.get("attrs", {}).get("severity", "medium")),
        status=str(decision["status"]),
        score=float(decision["score"]),
        evaluation_id=evaluation_id,
        sarif_path=str(sarif_path),
    )


def _write_verification_event(
    result: GateResult,
    facts: dict[str, Any],
) -> GateIssue | None:
    """Write a verification event for a successful evaluation."""
    event = {
        "requirement_uid": result.requirement_uid,
        "target": facts.get("target", {}),
        "decision": {
            "status": result.status,
            "score": result.score,
            "confidence": 0.8,
        },
        "sarif_ref": result.sarif_path,
    }
    verification_writer = cast(Callable[[dict[str, Any]], dict[str, Any]], reqif_write_verification)
    write_result = verification_writer(event)
    if "error" in write_result:
        error = write_result.get("error", {})
        return GateIssue(
            code="VERIFICATION_WRITE_FAILED",
            stage="verification",
            message=str(error.get("message", "Verification writer returned an unspecified error")),
            requirement_uid=result.requirement_uid,
            requirement_key=result.requirement_key,
        )
    return None


def _derive_gate_failures(results: list[GateResult]) -> list[GateIssue]:
    """Derive gate failures from successful evaluation outcomes."""
    failures: list[GateIssue] = []
    for result in results:
        if result.status == "fail" and result.severity in {"high", "critical"}:
            failures.append(
                GateIssue(
                    code="HIGH_SEVERITY_POLICY_FAILURE",
                    stage="gate",
                    message=(
                        f"Requirement {result.requirement_key or result.requirement_uid} failed with "
                        f"{result.severity} severity."
                    ),
                    requirement_uid=result.requirement_uid,
                    requirement_key=result.requirement_key,
                )
            )
    return failures


def _gate_status(
    meta_policy_failures: list[GateIssue],
    processing_failures: list[GateIssue],
    gate_failures: list[GateIssue],
) -> str:
    """Map collected issues to a top-level gate status."""
    if meta_policy_failures:
        return "failed_meta_policy"
    if processing_failures:
        return "failed_processing"
    if gate_failures:
        return "failed_gate"
    return "passed"


def _persist_outputs(
    out_dir: Path,
    results: list[GateResult],
    summary: GateSummary,
) -> None:
    """Persist all gate outputs even on partial failures."""
    _write_json(out_dir / "compliance_results.json", [asdict(result) for result in results])
    _write_json(out_dir / "compliance_summary.json", asdict(summary))
    (out_dir / "compliance_summary.md").write_text(
        _render_summary_markdown(summary),
        encoding="utf-8",
    )
    try:
        _write_merged_sarif(out_dir, results)
    except Exception as exc:
        summary.processing_failures.append(
            GateIssue(
                code="SARIF_MERGE_FAILED",
                stage="sarif",
                message=f"{type(exc).__name__}: {exc}",
            )
        )
        summary.processing_failure_count = len(summary.processing_failures)
        summary.gate_status = _gate_status(
            summary.meta_policy_failures,
            summary.processing_failures,
            summary.gate_failures,
        )
        _write_json(out_dir / "compliance_summary.json", asdict(summary))
        (out_dir / "compliance_summary.md").write_text(
            _render_summary_markdown(summary),
            encoding="utf-8",
        )
        _write_json(
            out_dir / "merged.sarif",
            {
                "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
                "version": "2.1.0",
                "runs": [],
            },
        )


def _write_merged_sarif(out_dir: Path, results: list[GateResult]) -> None:
    """Merge per-evaluation SARIF files into one report."""
    all_runs: list[dict[str, Any]] = []
    for result in results:
        with Path(result.sarif_path).open(encoding="utf-8") as handle:
            sarif_report = json.load(handle)
        all_runs.extend(sarif_report.get("runs", []))

    merged_sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": all_runs,
    }
    _write_json(out_dir / "merged.sarif", merged_sarif)


def _render_summary_markdown(summary: GateSummary) -> str:
    """Render a human-readable markdown summary."""
    lines = [
        f"## Compliance Gate Summary - {summary.gate_status}",
        "",
        f"- Subtype: {summary.subtype}",
        f"- Baseline requirements: {summary.baseline_requirement_count}",
        f"- Selected requirements: {summary.selected_requirement_count}",
        f"- Attempted evaluations: {summary.attempted_evaluations}",
        f"- Successful evaluations: {summary.successful_evaluations}",
        f"- Verification events written: {summary.verification_events_written}",
        f"- Meta-policy failures: {summary.meta_policy_failure_count}",
        f"- Processing failures: {summary.processing_failure_count}",
        f"- Gate failures: {summary.gate_failure_count}",
    ]

    if summary.applied_filters:
        lines.append(f"- Applied filters: {summary.applied_filters}")

    if summary.result_counts:
        lines.append(f"- Result counts: {summary.result_counts}")

    for title, issues in (
        ("Meta-policy failures", summary.meta_policy_failures),
        ("Processing failures", summary.processing_failures),
        ("Gate failures", summary.gate_failures),
    ):
        if not issues:
            continue
        lines.append("")
        lines.append(f"### {title}")
        for issue in issues:
            requirement = issue.requirement_key or issue.requirement_uid or "global"
            lines.append(f"- {issue.code} [{requirement}] {issue.message}")

    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    """Write deterministic JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _print_summary(summary: GateSummary) -> None:
    """Print a concise but explicit console summary."""
    print("Compliance Gate Summary")
    print(f"  gate_status: {summary.gate_status}")
    print(f"  subtype: {summary.subtype}")
    print(f"  baseline_requirement_count: {summary.baseline_requirement_count}")
    print(f"  selected_requirement_count: {summary.selected_requirement_count}")
    print(f"  attempted_evaluations: {summary.attempted_evaluations}")
    print(f"  successful_evaluations: {summary.successful_evaluations}")
    print(f"  verification_events_written: {summary.verification_events_written}")
    print(f"  applied_filters: {summary.applied_filters}")
    print(f"  result_counts: {summary.result_counts}")
    print(f"  meta_policy_failure_count: {summary.meta_policy_failure_count}")
    print(f"  processing_failure_count: {summary.processing_failure_count}")
    print(f"  gate_failure_count: {summary.gate_failure_count}")

    for label, issues in (
        ("meta_policy_failures", summary.meta_policy_failures),
        ("processing_failures", summary.processing_failures),
        ("gate_failures", summary.gate_failures),
    ):
        print(f"  {label}: {len(issues)}")
        for issue in issues:
            requirement = issue.requirement_key or issue.requirement_uid or "global"
            print(f"    - {issue.code} [{requirement}] {issue.message}")


def _find_duplicates(values: Iterable[str]) -> list[str]:
    """Return duplicate non-empty values in deterministic order."""
    counts = Counter(str(value) for value in values if str(value).strip())
    return sorted(value for value, count in counts.items() if count > 1)


if __name__ == "__main__":
    main()
