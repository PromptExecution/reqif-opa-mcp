#!/usr/bin/env python3
"""Stub agent for testing compliance gate system.

This agent generates synthetic facts and evidence for testing purposes.
It does NOT perform actual analysis - it returns mock data appropriate
for the given requirement subtype.

Usage:
    python agents/stub_agent.py --subtype CYBER
    python agents/stub_agent.py --subtype ACCESS_CONTROL
"""

import argparse
import json
import sys
from typing import Any


def generate_stub_facts(subtype: str) -> dict[str, Any]:
    """Generate synthetic facts appropriate for the given subtype.

    Args:
        subtype: Requirement subtype string (e.g., "CYBER", "ACCESS_CONTROL")

    Returns:
        Facts object conforming to facts/1 schema with synthetic data
    """
    # Define synthetic facts per subtype
    facts_by_subtype: dict[str, dict[str, Any]] = {
        "CYBER": {
            "uses_crypto_library": True,
            "crypto_algorithms": ["AES-256-GCM", "SHA-256"],
            "inputs_validated": [
                {"path": "src/api/auth.py", "line": 44, "kind": "missing"}
            ],
            "security_headers_enabled": True,
            "tls_version": "1.3",
        },
        "ACCESS_CONTROL": {
            "authentication_required": True,
            "authorization_mechanism": "RBAC",
            "rbac_roles_defined": ["admin", "user", "auditor"],
            "session_timeout_seconds": 1800,
            "multi_factor_auth_enabled": False,
        },
        "DATA_PRIVACY": {
            "pii_fields_encrypted": ["ssn", "email", "phone"],
            "data_retention_policy_days": 90,
            "gdpr_compliant_deletion": True,
            "consent_tracking_enabled": True,
        },
        "AUDIT": {
            "audit_logging_enabled": True,
            "log_retention_days": 365,
            "log_integrity_protection": "cryptographic_hash",
            "audit_events_captured": [
                "login", "logout", "data_access", "data_modification"
            ],
        },
    }

    # Get facts for subtype, or use generic default
    facts = facts_by_subtype.get(
        subtype,
        {
            "analysis_performed": True,
            "subtype": subtype,
            "stub_agent_note": f"No specific facts defined for {subtype}",
        }
    )

    return facts


def generate_stub_evidence(subtype: str) -> list[dict[str, Any]]:
    """Generate synthetic evidence pointers for the given subtype.

    Args:
        subtype: Requirement subtype string

    Returns:
        Evidence array with code_span and artifact evidence items
    """
    # Base repository information
    repo_base = "repo://github.com/example/target-system"

    # Evidence patterns per subtype
    evidence_by_subtype: dict[str, list[dict[str, Any]]] = {
        "CYBER": [
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/crypto/encryption.py",
                "startLine": 15,
                "endLine": 42,
            },
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/api/auth.py",
                "startLine": 44,
                "endLine": 44,
            },
            {
                "type": "artifact",
                "uri": "artifact://sbom.cdx.json",
                "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
        ],
        "ACCESS_CONTROL": [
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/auth/rbac.py",
                "startLine": 10,
                "endLine": 55,
            },
            {
                "type": "code_span",
                "uri": f"{repo_base}/config/permissions.yaml",
                "startLine": 1,
                "endLine": 30,
            },
        ],
        "DATA_PRIVACY": [
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/models/user.py",
                "startLine": 20,
                "endLine": 35,
            },
            {
                "type": "artifact",
                "uri": "artifact://privacy-policy.pdf",
                "hash": "sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2",
            },
        ],
        "AUDIT": [
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/logging/audit.py",
                "startLine": 5,
                "endLine": 80,
            },
            {
                "type": "log",
                "uri": "file:///var/log/audit/audit.log",
            },
        ],
    }

    # Get evidence for subtype, or use generic default
    evidence = evidence_by_subtype.get(
        subtype,
        [
            {
                "type": "code_span",
                "uri": f"{repo_base}/src/main.py",
                "startLine": 1,
                "endLine": 100,
            }
        ]
    )

    return evidence


def create_facts_output(subtype: str) -> dict[str, Any]:
    """Create complete facts/1 output for the given subtype.

    Args:
        subtype: Requirement subtype string

    Returns:
        Complete facts object conforming to facts/1 schema
    """
    return {
        "target": {
            "repo": "github.com/example/target-system",
            "commit": "abc123def456789012345678901234567890abcd",
            "build": "build-2026-01-31-001",
        },
        "facts": generate_stub_facts(subtype),
        "evidence": generate_stub_evidence(subtype),
        "agent": {
            "name": "stub-agent",
            "version": "0.1.0",
            "rubric_hint": f"compliance.{subtype.lower()}",
        },
    }


def main() -> None:
    """Main entry point for stub agent CLI."""
    parser = argparse.ArgumentParser(
        description="Stub agent for testing compliance gate system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents/stub_agent.py --subtype CYBER
  python agents/stub_agent.py --subtype ACCESS_CONTROL
  python agents/stub_agent.py --subtype DATA_PRIVACY
        """,
    )
    parser.add_argument(
        "--subtype",
        type=str,
        required=True,
        help="Requirement subtype to generate facts for (e.g., CYBER, ACCESS_CONTROL)",
    )

    args = parser.parse_args()

    # Generate facts output
    facts_output = create_facts_output(args.subtype)

    # Output JSON to stdout
    json.dump(facts_output, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
