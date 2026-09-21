"""
Tests for _active_policy_rules (app/api/providers.py): merging rules across
ALL active policies of an org. This is the logic that was buggy — it used
to pick one arbitrary active policy; now it merges blocked_terms from every
active policy's latest APPROVED version and requires approval if any does.

These drive the helper directly against the test DB via small fixtures.
"""

import pytest

from app.api.providers import _active_policy_rules
from app.models.ai_policy import AIPolicy, AIPolicyVersion

pytestmark = pytest.mark.asyncio


async def _make_policy(db, org_id, status, versions, approver_id):
    """versions = list of (version_no, rules_json, approved) tuples."""
    policy = AIPolicy(org_id=org_id, name=f"p-{status}-{id(versions)}", status=status)
    db.add(policy)
    await db.flush()
    for vno, rules, approved in versions:
        db.add(AIPolicyVersion(
            policy_id=policy.id, version=vno, rules_json=rules,
            approved_by=(approver_id if approved else None),
        ))
    await db.flush()
    return policy


async def test_no_active_policies_returns_empty(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    rules = await _active_policy_rules(db_session, org_id)
    assert rules == {}


async def test_single_active_policy_blocked_terms(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    await _make_policy(db_session, org_id, "active", [(1, {"blocked_terms": ["secret"]}, True)], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    assert rules.get("blocked_terms") == ["secret"]


async def test_merges_blocked_terms_across_active_policies(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    await _make_policy(db_session, org_id, "active", [(1, {"blocked_terms": ["alpha"]}, True)], admin_id)
    await _make_policy(db_session, org_id, "active", [(1, {"blocked_terms": ["beta", "gamma"]}, True)], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    terms = set(rules.get("blocked_terms") or [])
    # the old bug returned only ONE policy's terms; now all merge
    assert terms == {"alpha", "beta", "gamma"}


async def test_latest_approved_version_wins(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    # v1 approved with 'old', v2 approved with 'new' -> v2 (latest) used
    await _make_policy(db_session, org_id, "active", [
        (1, {"blocked_terms": ["old"]}, True),
        (2, {"blocked_terms": ["new"]}, True),
    ], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    assert rules.get("blocked_terms") == ["new"]


async def test_unapproved_latest_version_is_ignored(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    # v1 approved (blocked), v2 NOT approved -> falls back to v1
    # (this is exactly the situation that caused the live bug)
    await _make_policy(db_session, org_id, "active", [
        (1, {"effect": "require_approval"}, True),
        (2, {"blocked_terms": ["shouldnotapply"]}, False),
    ], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    assert rules.get("effect") == "require_approval"
    assert "blocked_terms" not in rules  # v2 unapproved, ignored


async def test_archived_policy_does_not_apply(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    await _make_policy(db_session, org_id, "archived", [(1, {"blocked_terms": ["archived_term"]}, True)], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    assert rules == {}


async def test_require_approval_if_any_policy_requires(db_session, org_and_users):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    await _make_policy(db_session, org_id, "active", [(1, {"blocked_terms": ["x"]}, True)], admin_id)
    await _make_policy(db_session, org_id, "active", [(1, {"effect": "require_approval"}, True)], admin_id)
    rules = await _active_policy_rules(db_session, org_id)
    assert rules.get("effect") == "require_approval"
    assert "x" in (rules.get("blocked_terms") or [])
