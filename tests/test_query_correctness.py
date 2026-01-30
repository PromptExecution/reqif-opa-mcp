"""Unit tests for requirement query filtering correctness.

Tests verify that reqif.query filtering logic works correctly for:
- Single subtype filtering
- Multiple subtypes (AND logic)
- Baseline filtering
- Pagination consistency (limit/offset)
- Empty query results
"""

from reqif_mcp.server import _baseline_store, query_requirements, store_baseline


def test_filter_by_single_subtype() -> None:
    """Test that filtering by single subtype returns correct subset."""
    # Create test baseline with mixed subtypes
    test_requirements = [
        {
            "uid": "req-001",
            "key": "CYBER-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Crypto requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-002",
            "key": "AC-001",
            "subtypes": ["ACCESS_CONTROL"],
            "status": "active",
            "text": "Access control requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-003",
            "key": "CYBER-002",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Another crypto requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-004",
            "key": "AUDIT-001",
            "subtypes": ["AUDIT"],
            "status": "active",
            "text": "Audit requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
    ]

    store_baseline("test-handle-001", test_requirements)

    # Query for CYBER subtype only
    result = query_requirements(handle="test-handle-001", subtypes=["CYBER"])

    # Verify results
    assert isinstance(result, dict)
    assert result["total_count"] == 2
    assert result["returned_count"] == 2
    assert len(result["requirements"]) == 2

    # Verify only CYBER requirements returned
    for req in result["requirements"]:
        assert "CYBER" in req["subtypes"]

    # Verify correct requirements by uid (sorted order)
    assert result["requirements"][0]["uid"] == "req-001"
    assert result["requirements"][1]["uid"] == "req-003"

    # Cleanup
    _baseline_store.clear()


def test_filter_by_multiple_subtypes_and_logic() -> None:
    """Test that filtering by multiple subtypes uses AND logic (all must match)."""
    # Create test baseline with single and multi-subtype requirements
    test_requirements = [
        {
            "uid": "req-001",
            "key": "CYBER-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Only CYBER",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-002",
            "key": "AC-001",
            "subtypes": ["ACCESS_CONTROL"],
            "status": "active",
            "text": "Only ACCESS_CONTROL",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-003",
            "key": "CYBER-AC-001",
            "subtypes": ["CYBER", "ACCESS_CONTROL"],
            "status": "active",
            "text": "Both CYBER and ACCESS_CONTROL",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-004",
            "key": "CYBER-AC-002",
            "subtypes": ["CYBER", "ACCESS_CONTROL", "AUDIT"],
            "status": "active",
            "text": "CYBER, ACCESS_CONTROL, and AUDIT",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
    ]

    store_baseline("test-handle-002", test_requirements)

    # Query for requirements with BOTH CYBER AND ACCESS_CONTROL
    result = query_requirements(handle="test-handle-002", subtypes=["CYBER", "ACCESS_CONTROL"])

    # Verify results - should only return requirements with BOTH subtypes
    assert isinstance(result, dict)
    assert result["total_count"] == 2
    assert result["returned_count"] == 2
    assert len(result["requirements"]) == 2

    # Verify all requirements have both subtypes
    for req in result["requirements"]:
        assert "CYBER" in req["subtypes"]
        assert "ACCESS_CONTROL" in req["subtypes"]

    # Verify correct requirements by uid (sorted order)
    assert result["requirements"][0]["uid"] == "req-003"
    assert result["requirements"][1]["uid"] == "req-004"

    # Cleanup
    _baseline_store.clear()


def test_filter_by_baseline() -> None:
    """Test that filtering by baseline returns only requirements from that baseline."""
    # Create two separate baselines
    baseline_a_requirements = [
        {
            "uid": "req-a-001",
            "key": "A-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Baseline A requirement 1",
            "policy_baseline": {"id": "baseline-a", "version": "1.0", "hash": "aaa111"},
            "rubrics": [],
        },
        {
            "uid": "req-a-002",
            "key": "A-002",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Baseline A requirement 2",
            "policy_baseline": {"id": "baseline-a", "version": "1.0", "hash": "aaa111"},
            "rubrics": [],
        },
    ]

    baseline_b_requirements = [
        {
            "uid": "req-b-001",
            "key": "B-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Baseline B requirement 1",
            "policy_baseline": {"id": "baseline-b", "version": "2.0", "hash": "bbb222"},
            "rubrics": [],
        },
        {
            "uid": "req-b-002",
            "key": "B-002",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Baseline B requirement 2",
            "policy_baseline": {"id": "baseline-b", "version": "2.0", "hash": "bbb222"},
            "rubrics": [],
        },
    ]

    store_baseline("handle-baseline-a", baseline_a_requirements)
    store_baseline("handle-baseline-b", baseline_b_requirements)

    # Query baseline A
    result_a = query_requirements(handle="handle-baseline-a")
    assert isinstance(result_a, dict)
    assert result_a["total_count"] == 2
    assert result_a["requirements"][0]["uid"] == "req-a-001"
    assert result_a["requirements"][1]["uid"] == "req-a-002"
    assert all(req["policy_baseline"]["id"] == "baseline-a" for req in result_a["requirements"])

    # Query baseline B
    result_b = query_requirements(handle="handle-baseline-b")
    assert isinstance(result_b, dict)
    assert result_b["total_count"] == 2
    assert result_b["requirements"][0]["uid"] == "req-b-001"
    assert result_b["requirements"][1]["uid"] == "req-b-002"
    assert all(req["policy_baseline"]["id"] == "baseline-b" for req in result_b["requirements"])

    # Cleanup
    _baseline_store.clear()


def test_pagination_with_limit_and_offset() -> None:
    """Test that pagination with limit/offset returns consistent results."""
    # Create test baseline with 10 requirements
    test_requirements = [
        {
            "uid": f"req-{i:03d}",
            "key": f"TEST-{i:03d}",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": f"Requirement {i}",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        }
        for i in range(1, 11)
    ]

    store_baseline("test-handle-004", test_requirements)

    # Query with limit=3, offset=0 (first page)
    page_1 = query_requirements(handle="test-handle-004", limit=3, offset=0)
    assert isinstance(page_1, dict)
    assert page_1["total_count"] == 3
    assert page_1["returned_count"] == 3
    assert page_1["offset"] == 0
    assert len(page_1["requirements"]) == 3
    assert page_1["requirements"][0]["uid"] == "req-001"
    assert page_1["requirements"][1]["uid"] == "req-002"
    assert page_1["requirements"][2]["uid"] == "req-003"

    # Query with limit=3, offset=3 (second page)
    page_2 = query_requirements(handle="test-handle-004", limit=3, offset=3)
    assert isinstance(page_2, dict)
    assert page_2["total_count"] == 3
    assert page_2["returned_count"] == 3
    assert page_2["offset"] == 3
    assert len(page_2["requirements"]) == 3
    assert page_2["requirements"][0]["uid"] == "req-004"
    assert page_2["requirements"][1]["uid"] == "req-005"
    assert page_2["requirements"][2]["uid"] == "req-006"

    # Query with limit=3, offset=6 (third page)
    page_3 = query_requirements(handle="test-handle-004", limit=3, offset=6)
    assert isinstance(page_3, dict)
    assert page_3["total_count"] == 3
    assert page_3["returned_count"] == 3
    assert page_3["offset"] == 6
    assert len(page_3["requirements"]) == 3
    assert page_3["requirements"][0]["uid"] == "req-007"
    assert page_3["requirements"][1]["uid"] == "req-008"
    assert page_3["requirements"][2]["uid"] == "req-009"

    # Query with limit=3, offset=9 (fourth page, partial)
    page_4 = query_requirements(handle="test-handle-004", limit=3, offset=9)
    assert isinstance(page_4, dict)
    assert page_4["total_count"] == 1
    assert page_4["returned_count"] == 1
    assert page_4["offset"] == 9
    assert len(page_4["requirements"]) == 1
    assert page_4["requirements"][0]["uid"] == "req-010"

    # Verify consistency: querying all requirements at once should match paginated results
    all_results = query_requirements(handle="test-handle-004")
    assert isinstance(all_results, dict)
    paginated_uids = (
        [r["uid"] for r in page_1["requirements"]] +
        [r["uid"] for r in page_2["requirements"]] +
        [r["uid"] for r in page_3["requirements"]] +
        [r["uid"] for r in page_4["requirements"]]
    )
    all_uids = [r["uid"] for r in all_results["requirements"]]
    assert paginated_uids == all_uids

    # Cleanup
    _baseline_store.clear()


def test_query_with_no_matches() -> None:
    """Test that query with no matches returns empty array (not error)."""
    # Create test baseline with specific subtypes
    test_requirements = [
        {
            "uid": "req-001",
            "key": "CYBER-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Cyber requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-002",
            "key": "AC-001",
            "subtypes": ["ACCESS_CONTROL"],
            "status": "active",
            "text": "Access control requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
    ]

    store_baseline("test-handle-005", test_requirements)

    # Query for non-existent subtype
    result = query_requirements(handle="test-handle-005", subtypes=["DATA_PRIVACY"])

    # Verify empty result set (not error)
    assert isinstance(result, dict)
    assert result["total_count"] == 0
    assert result["returned_count"] == 0
    assert result["requirements"] == []

    # Query for non-existent status
    result_status = query_requirements(handle="test-handle-005", status="obsolete")
    assert isinstance(result_status, dict)
    assert result_status["total_count"] == 0
    assert result_status["returned_count"] == 0
    assert result_status["requirements"] == []

    # Query for combination that doesn't exist (CYBER + ACCESS_CONTROL together)
    result_combo = query_requirements(handle="test-handle-005", subtypes=["CYBER", "ACCESS_CONTROL"])
    assert isinstance(result_combo, dict)
    assert result_combo["total_count"] == 0
    assert result_combo["returned_count"] == 0
    assert result_combo["requirements"] == []

    # Cleanup
    _baseline_store.clear()


def test_filter_by_status() -> None:
    """Test that filtering by status works correctly."""
    # Create test baseline with mixed statuses
    test_requirements = [
        {
            "uid": "req-001",
            "key": "TEST-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Active requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-002",
            "key": "TEST-002",
            "subtypes": ["CYBER"],
            "status": "obsolete",
            "text": "Obsolete requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-003",
            "key": "TEST-003",
            "subtypes": ["CYBER"],
            "status": "draft",
            "text": "Draft requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-004",
            "key": "TEST-004",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Another active requirement",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
    ]

    store_baseline("test-handle-006", test_requirements)

    # Query for active status
    result_active = query_requirements(handle="test-handle-006", status="active")
    assert isinstance(result_active, dict)
    assert result_active["total_count"] == 2
    assert len(result_active["requirements"]) == 2
    assert all(req["status"] == "active" for req in result_active["requirements"])
    assert result_active["requirements"][0]["uid"] == "req-001"
    assert result_active["requirements"][1]["uid"] == "req-004"

    # Query for obsolete status
    result_obsolete = query_requirements(handle="test-handle-006", status="obsolete")
    assert isinstance(result_obsolete, dict)
    assert result_obsolete["total_count"] == 1
    assert len(result_obsolete["requirements"]) == 1
    assert result_obsolete["requirements"][0]["status"] == "obsolete"
    assert result_obsolete["requirements"][0]["uid"] == "req-002"

    # Query for draft status
    result_draft = query_requirements(handle="test-handle-006", status="draft")
    assert isinstance(result_draft, dict)
    assert result_draft["total_count"] == 1
    assert len(result_draft["requirements"]) == 1
    assert result_draft["requirements"][0]["status"] == "draft"
    assert result_draft["requirements"][0]["uid"] == "req-003"

    # Cleanup
    _baseline_store.clear()


def test_deterministic_ordering_across_queries() -> None:
    """Test that same query returns results in same order (deterministic)."""
    # Create test baseline with requirements in random uid order
    test_requirements = [
        {
            "uid": "req-005",
            "key": "TEST-005",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Requirement 5",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-001",
            "key": "TEST-001",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Requirement 1",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-003",
            "key": "TEST-003",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Requirement 3",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
        {
            "uid": "req-002",
            "key": "TEST-002",
            "subtypes": ["CYBER"],
            "status": "active",
            "text": "Requirement 2",
            "policy_baseline": {"id": "test-baseline", "version": "1.0", "hash": "abc123"},
            "rubrics": [],
        },
    ]

    store_baseline("test-handle-007", test_requirements)

    # Query multiple times with same parameters
    result_1 = query_requirements(handle="test-handle-007", subtypes=["CYBER"])
    result_2 = query_requirements(handle="test-handle-007", subtypes=["CYBER"])
    result_3 = query_requirements(handle="test-handle-007", subtypes=["CYBER"])

    # Extract UIDs from each result
    uids_1 = [req["uid"] for req in result_1["requirements"]]
    uids_2 = [req["uid"] for req in result_2["requirements"]]
    uids_3 = [req["uid"] for req in result_3["requirements"]]

    # Verify all queries return same order
    assert uids_1 == uids_2
    assert uids_2 == uids_3

    # Verify order is sorted by uid (ascending)
    assert uids_1 == ["req-001", "req-002", "req-003", "req-005"]

    # Cleanup
    _baseline_store.clear()
