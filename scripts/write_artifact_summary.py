#!/usr/bin/env python3
"""Write compact markdown and JSON summaries for self-test and demo artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write artifact summaries")
    parser.add_argument("--mode", choices=("selftest", "demo"), required=True)
    parser.add_argument("--root", required=True, help="Artifact root directory")
    parser.add_argument("--summary-markdown", required=True, help="Markdown output path")
    parser.add_argument("--summary-json", required=True, help="JSON output path")
    args = parser.parse_args()

    root = Path(args.root)
    payload = build_summary(mode=args.mode, root=root)
    markdown_path = Path(args.summary_markdown)
    json_path = Path(args.summary_json)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_summary(mode: str, root: Path) -> dict[str, Any]:
    """Build a structured summary payload from known artifact locations."""
    reqif_dir = root / ("reqif" if mode == "demo" else "ingest")
    selftest_dir = root / ("selftest" if mode == "demo" else ".")
    checks = [
        read_gate_summary("asvs", selftest_dir / "asvs"),
        read_gate_summary("ssdf", selftest_dir / "ssdf"),
    ]
    reqif_outputs = sorted(str(path) for path in reqif_dir.glob("*.reqif")) if reqif_dir.exists() else []
    statuses = [check["gate_status"] for check in checks if check["present"]]
    overall_status = "passed" if statuses and all(status == "passed" for status in statuses) else "issues_detected"

    return {
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "overall_status": overall_status,
        "reqif_outputs": reqif_outputs,
        "checks": checks,
    }


def read_gate_summary(name: str, root: Path) -> dict[str, Any]:
    """Read one compliance-gate summary directory if present."""
    summary_path = root / "compliance_summary.json"
    if not summary_path.exists():
        return {
            "name": name,
            "present": False,
            "gate_status": "missing",
            "summary_path": str(summary_path),
            "merged_sarif": str(root / "merged.sarif"),
            "evidence_dir": str(root / "evidence_store"),
        }

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "name": name,
        "present": True,
        "gate_status": summary.get("gate_status", "unknown"),
        "result_counts": summary.get("result_counts", {}),
        "summary_path": str(summary_path),
        "summary_markdown": str(root / "compliance_summary.md"),
        "merged_sarif": str(root / "merged.sarif"),
        "evidence_dir": str(root / "evidence_store"),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render a compact markdown summary."""
    lines = [
        f"# {payload['mode'].title()} Artifact Summary",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Root: `{payload['root']}`",
        f"- Overall status: `{payload['overall_status']}`",
        "",
        "## Derived ReqIF Outputs",
    ]

    if payload["reqif_outputs"]:
        lines.extend(f"- `{path}`" for path in payload["reqif_outputs"])
    else:
        lines.append("- none found")

    lines.extend(["", "## Compliance Checks"])
    for check in payload["checks"]:
        lines.append(f"- `{check['name']}`: `{check['gate_status']}`")
        if check.get("present"):
            lines.append(f"  - summary: `{check['summary_path']}`")
            lines.append(f"  - sarif: `{check['merged_sarif']}`")
            lines.append(f"  - evidence: `{check['evidence_dir']}`")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
