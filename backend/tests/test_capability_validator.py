"""
Tests for app.services.capability_validator - the subset check that
prevents an agent from delegating more than it holds. Getting this wrong
would let a low-privilege agent hand out capabilities it never had, which
is the core escalation risk the governance module exists to stop.

Pure functions, no DB.
"""

import pytest

from app.services.capability_validator import (
    is_subset,
    escalated_items,
    validate_delegation,
    effective_capabilities_for_hop,
)


class TestIsSubset:
    def test_true_subset(self):
        assert is_subset(["a"], ["a", "b"]) is True

    def test_equal_sets(self):
        assert is_subset(["a", "b"], ["a", "b"]) is True

    def test_empty_child_is_subset(self):
        assert is_subset([], ["a"]) is True
        assert is_subset(None, None) is True

    def test_not_subset(self):
        assert is_subset(["a", "c"], ["a", "b"]) is False

    def test_anything_not_subset_of_empty(self):
        assert is_subset(["a"], []) is False


class TestEscalatedItems:
    def test_lists_the_escalated(self):
        assert escalated_items(["a", "c", "d"], ["a"]) == ["c", "d"]

    def test_none_when_within(self):
        assert escalated_items(["a"], ["a", "b"]) == []

    def test_sorted_output(self):
        # stable, sorted for predictable incident logging
        assert escalated_items(["z", "a"], []) == ["a", "z"]


class TestValidateDelegation:
    def test_ok_when_subset(self):
        ok, escalated = validate_delegation(["read"], ["read", "write"])
        assert ok is True and escalated == []

    def test_flags_escalation(self):
        ok, escalated = validate_delegation(["read", "admin"], ["read"])
        assert ok is False and escalated == ["admin"]

    def test_empty_delegation_is_ok(self):
        ok, escalated = validate_delegation([], ["read"])
        assert ok is True and escalated == []


class TestEffectiveCapabilities:
    def test_clamps_to_intersection(self):
        assert effective_capabilities_for_hop(["read", "admin"], ["read", "write"]) == ["read"]

    def test_empty_when_no_overlap(self):
        assert effective_capabilities_for_hop(["admin"], ["read"]) == []

    def test_full_when_all_granted(self):
        assert effective_capabilities_for_hop(["read", "write"], ["read", "write", "x"]) == ["read", "write"]
