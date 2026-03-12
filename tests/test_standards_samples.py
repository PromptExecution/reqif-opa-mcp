"""Tests for the downloaded standards-derived sample baselines."""

from __future__ import annotations

from pathlib import Path

from returns.result import Success

from reqif_mcp.normalization import normalize_reqif
from reqif_mcp.reqif_parser import parse_reqif_xml


OWASP_SAMPLE = Path("samples/standards/derived/owasp_asvs_cwe.reqif")
SSDF_SAMPLE = Path("samples/standards/derived/nist_ssdf_dogfood.reqif")


def test_owasp_asvs_sample_reqif_normalizes_with_cwe_attrs() -> None:
    """OWASP ASVS sample controls should preserve their CWE metadata."""
    parse_result = parse_reqif_xml(OWASP_SAMPLE)
    assert isinstance(parse_result, Success)

    normalize_result = normalize_reqif(parse_result.unwrap(), "ASVS", "5.0.0")
    assert isinstance(normalize_result, Success)

    requirements = normalize_result.unwrap()
    assert len(requirements) == 7
    assert {req["attrs"]["cwe"] for req in requirements} == {
        "CWE-20",
        "CWE-22",
        "CWE-78",
        "CWE-400",
        "CWE-532",
        "CWE-862",
        "CWE-918",
    }


def test_nist_ssdf_sample_reqif_normalizes_with_control_ids() -> None:
    """NIST SSDF sample tasks should preserve their task identifiers."""
    parse_result = parse_reqif_xml(SSDF_SAMPLE)
    assert isinstance(parse_result, Success)

    normalize_result = normalize_reqif(parse_result.unwrap(), "SSDF", "1.1")
    assert isinstance(normalize_result, Success)

    requirements = normalize_result.unwrap()
    assert len(requirements) == 4
    assert {req["attrs"]["control_id"] for req in requirements} == {
        "PO.3.1",
        "PW.7.2",
        "RV.1.2",
        "RV.1.3",
    }
