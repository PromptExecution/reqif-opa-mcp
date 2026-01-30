"""
Unit tests for ReqIF normalization module.

Tests cover:
- Deterministic UID generation from ReqIF identifiers
- Stable UID across multiple normalization runs
- Valid identifiers passing through unchanged
- UUID v5-based UID generation for invalid identifiers
"""

from reqif_mcp.normalization import _extract_or_generate_uid


def test_deterministic_uid_generation() -> None:
    """Test that UIDs are deterministically generated from identifiers."""
    
    # Identifiers with special characters that need hashing
    test_identifiers = [
        "REQ-001 (Special!)",
        "REQ/002",
        "REQ#003",
        "Requirement 123",
        "REQ.004",
        "REQ@005",
    ]
    
    for identifier in test_identifiers:
        # Generate UID multiple times
        uid1 = _extract_or_generate_uid(identifier)
        uid2 = _extract_or_generate_uid(identifier)
        uid3 = _extract_or_generate_uid(identifier)
        
        # All UIDs should be identical (deterministic)
        assert uid1 == uid2, f"UIDs not deterministic for '{identifier}': {uid1} != {uid2}"
        assert uid2 == uid3, f"UIDs not deterministic for '{identifier}': {uid2} != {uid3}"
        
        # UID should be a valid UUID format
        assert len(uid1) == 36, f"UID not valid UUID format: {uid1}"
        assert uid1.count('-') == 4, f"UID not valid UUID format: {uid1}"


def test_valid_identifiers_unchanged() -> None:
    """Test that valid alphanumeric identifiers pass through unchanged."""
    
    valid_identifiers = [
        "REQ-001",
        "REQ_002",
        "abc123",
        "ABC-DEF_123",
        "requirement-001",
        "CYBER-ENC-001",
        "AC_AUTH_001",
    ]
    
    for identifier in valid_identifiers:
        uid = _extract_or_generate_uid(identifier)
        assert uid == identifier, f"Valid identifier was changed: '{identifier}' -> '{uid}'"


def test_uid_stability_across_normalization() -> None:
    """
    Test that the same ReqIF identifier produces the same UID across multiple
    normalization runs, ensuring stable SARIF rule IDs and traceability.
    """
    
    # Simulate the same identifier being processed multiple times
    # (e.g., across different pipeline runs or baseline updates)
    identifier = "REQ#123 (with special chars!)"
    
    # Simulate 10 normalization runs
    uids = [_extract_or_generate_uid(identifier) for _ in range(10)]
    
    # All UIDs should be identical
    assert len(set(uids)) == 1, f"UID not stable across runs: got {len(set(uids))} different values"
    
    # The stable UID should be deterministic
    expected_uid = _extract_or_generate_uid(identifier)
    assert all(uid == expected_uid for uid in uids), "Some UIDs don't match expected value"


def test_different_identifiers_produce_different_uids() -> None:
    """Test that different identifiers produce different UIDs."""
    
    identifiers = [
        "REQ#001",
        "REQ#002",
        "REQ#003",
        "Different requirement",
        "Another one",
    ]
    
    uids = [_extract_or_generate_uid(identifier) for identifier in identifiers]
    
    # All UIDs should be unique
    assert len(uids) == len(set(uids)), f"Some identifiers produced duplicate UIDs: {uids}"


def test_empty_identifier_handling() -> None:
    """Test handling of empty or whitespace identifiers."""
    
    # Empty string should generate a deterministic UID (not fail)
    uid1 = _extract_or_generate_uid("")
    uid2 = _extract_or_generate_uid("")
    
    # Should be deterministic even for empty string
    assert uid1 == uid2, "Empty string should produce deterministic UID"
    
    # Whitespace should also be handled deterministically
    uid_space1 = _extract_or_generate_uid("   ")
    uid_space2 = _extract_or_generate_uid("   ")
    assert uid_space1 == uid_space2, "Whitespace should produce deterministic UID"


def test_unicode_identifier_handling() -> None:
    """Test handling of Unicode characters in identifiers."""
    
    unicode_identifiers = [
        "REQ-日本語",
        "REQ-العربية",
        "REQ-中文",
        "Requirement™️",
    ]
    
    for identifier in unicode_identifiers:
        uid1 = _extract_or_generate_uid(identifier)
        uid2 = _extract_or_generate_uid(identifier)
        
        # Should be deterministic for Unicode
        assert uid1 == uid2, f"Unicode identifier not deterministic: '{identifier}'"
        
        # Should produce valid UUID format
        assert len(uid1) == 36, f"Unicode identifier produced invalid UID: {uid1}"


def test_case_sensitivity() -> None:
    """Test that UID generation is case-sensitive."""
    
    # Different cases should produce different results
    uid_lower = _extract_or_generate_uid("req-001 (test)")
    uid_upper = _extract_or_generate_uid("REQ-001 (TEST)")
    
    # These should be different due to case difference
    assert uid_lower != uid_upper, "Case difference should produce different UIDs"
    
    # But each should be deterministic
    assert uid_lower == _extract_or_generate_uid("req-001 (test)")
    assert uid_upper == _extract_or_generate_uid("REQ-001 (TEST)")
