"""
OPA evaluator module for executing policy evaluation via OPA subprocess.

This module provides functions to:
- Load OPA bundles from filesystem
- Compose OPA input JSON from requirement + facts + context
- Invoke OPA evaluation via subprocess
- Parse and return OPA decision output

All functions use Rust-style Result pattern for error handling.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from returns.result import Failure, Result, Success


def load_bundle_manifest(bundle_path: str | Path) -> Result[dict[str, Any], Exception]:
    """
    Load OPA bundle manifest file from bundle directory.

    Args:
        bundle_path: Path to OPA bundle directory containing .manifest file

    Returns:
        Result containing manifest dict or Exception if load fails
    """
    try:
        bundle_dir = Path(bundle_path)
        if not bundle_dir.is_dir():
            return Failure(ValueError(f"Bundle path is not a directory: {bundle_path}"))

        manifest_file = bundle_dir / ".manifest"
        if not manifest_file.exists():
            return Failure(
                ValueError(f"Bundle manifest not found: {manifest_file}")
            )

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        return Success(manifest)
    except json.JSONDecodeError as e:
        return Failure(ValueError(f"Invalid JSON in bundle manifest: {e}"))
    except Exception as e:
        return Failure(e)


def compose_opa_input(
    requirement: dict[str, Any],
    facts: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> Result[dict[str, Any], Exception]:
    """
    Compose OPA input JSON from requirement record, agent facts, and context.

    Args:
        requirement: Requirement record conforming to reqif-mcp/1 schema
        facts: Agent facts conforming to facts/1 schema
        context: Optional evaluation context (defaults to empty dict)

    Returns:
        Result containing OPA input dict or Exception if composition fails
    """
    try:
        opa_input = {
            "requirement": requirement,
            "facts": facts,
            "context": context if context is not None else {},
        }
        return Success(opa_input)
    except Exception as e:
        return Failure(e)


def evaluate_with_opa(
    opa_input: dict[str, Any],
    bundle_path: str | Path,
    package: str,
    rule: str,
    opa_binary: str = "opa",
) -> Result[dict[str, Any], Exception]:
    """
    Invoke OPA evaluation via subprocess and parse decision output.

    Args:
        opa_input: OPA input JSON dict (requirement + facts + context)
        bundle_path: Path to OPA bundle directory
        package: OPA package path (e.g., "cyber.access_control.v3")
        rule: OPA rule name (e.g., "decision")
        opa_binary: Path to OPA binary (defaults to "opa" in PATH)

    Returns:
        Result containing OPA decision output dict or Exception if evaluation fails
    """
    try:
        bundle_dir = Path(bundle_path)
        if not bundle_dir.is_dir():
            return Failure(ValueError(f"Bundle path is not a directory: {bundle_path}"))

        # Compose OPA eval query: package.rule
        query = f"data.{package}.{rule}"

        # Prepare input JSON
        input_json = json.dumps(opa_input)

        # Build OPA eval command
        # opa eval --bundle <bundle_path> --input <input.json> --format json <query>
        cmd = [
            opa_binary,
            "eval",
            "--bundle",
            str(bundle_dir),
            "--format",
            "json",
            "--stdin-input",
            query,
        ]

        # Execute OPA subprocess
        result = subprocess.run(
            cmd,
            input=input_json,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        # Check for OPA errors
        if result.returncode != 0:
            return Failure(
                RuntimeError(
                    f"OPA evaluation failed with exit code {result.returncode}: {result.stderr}"
                )
            )

        # Parse OPA output JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return Failure(
                ValueError(f"Invalid JSON in OPA output: {e}\nOutput: {result.stdout}")
            )

        # OPA eval returns {"result": [{"expressions": [{"value": <decision>}]}]}
        # Extract the decision value
        if "result" not in output:
            return Failure(ValueError("OPA output missing 'result' field"))

        if not output["result"]:
            return Failure(ValueError("OPA output 'result' is empty"))

        if "expressions" not in output["result"][0]:
            return Failure(
                ValueError("OPA output result missing 'expressions' field")
            )

        if not output["result"][0]["expressions"]:
            return Failure(ValueError("OPA output 'expressions' is empty"))

        decision = output["result"][0]["expressions"][0].get("value")
        if decision is None:
            return Failure(ValueError("OPA output expression missing 'value' field"))

        return Success(decision)
    except subprocess.TimeoutExpired:
        return Failure(RuntimeError("OPA evaluation timed out after 30 seconds"))
    except FileNotFoundError:
        return Failure(
            RuntimeError(
                f"OPA binary not found: {opa_binary}. Ensure OPA is installed and in PATH."
            )
        )
    except Exception as e:
        return Failure(e)


def evaluate_requirement(
    requirement: dict[str, Any],
    facts: dict[str, Any],
    bundle_path: str | Path,
    package: str | None = None,
    rule: str = "decision",
    context: dict[str, Any] | None = None,
    opa_binary: str = "opa",
) -> Result[dict[str, Any], Exception]:
    """
    High-level function to evaluate a requirement against facts using OPA.

    Composes OPA input, invokes evaluation, and returns decision output.

    Args:
        requirement: Requirement record conforming to reqif-mcp/1 schema
        facts: Agent facts conforming to facts/1 schema
        bundle_path: Path to OPA bundle directory
        package: OPA package path (if None, uses first rubric package from requirement)
        rule: OPA rule name (defaults to "decision")
        context: Optional evaluation context
        opa_binary: Path to OPA binary (defaults to "opa" in PATH)

    Returns:
        Result containing OPA decision output dict or Exception if evaluation fails
    """
    # Determine package from requirement rubrics if not provided
    if package is None:
        rubrics = requirement.get("rubrics", [])
        if not rubrics:
            return Failure(
                ValueError("Requirement has no rubrics and no package specified")
            )
        package = rubrics[0].get("package")
        if not package:
            return Failure(ValueError("Requirement rubric missing 'package' field"))

    # Compose OPA input
    input_result = compose_opa_input(requirement, facts, context)
    if isinstance(input_result, Failure):
        return input_result

    opa_input = input_result.unwrap()

    # Invoke OPA evaluation
    return evaluate_with_opa(opa_input, bundle_path, package, rule, opa_binary)
