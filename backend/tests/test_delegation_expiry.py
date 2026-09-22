"""
Tests for the delegation-expiry gate in check_action (feedback from an
automation PhD): an action must not run under a delegation that has already
expired. DB-free, like the rest of the policy-engine tests.
"""

from datetime import datetime, timezone, timedelta

from app.services.agent_policy_engine import (
    check_action,
    AgentView,
    ChainView,
    ActionContext,
    ALLOWED,
    DENIED,
)


def _agent(**kw):
    base = dict(
        allowed_tools=["openai.chat", "db.read"],
        allowed_models=["gpt-4o-mini"],
        max_delegation_depth=3,
        status="active",
    )
    base.update(kw)
    return AgentView(**base)


def _chain(**kw):
    base = dict(max_depth_reached=1, granted_capabilities=["read_analytics", "generate_text"])
    base.update(kw)
    return ChainView(**base)


def _ctx():
    return ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics"])


def _past():
    return datetime.now(timezone.utc) - timedelta(minutes=1)


def _future():
    return datetime.now(timezone.utc) + timedelta(minutes=10)


class TestDelegationExpiry:
    def test_expired_delegation_is_denied(self):
        d = check_action(_agent(), _chain(delegation_expires_at=_past()), _ctx())
        assert d.result == DENIED
        assert d.incident_type == "delegation_expired"

    def test_future_expiry_does_not_block(self):
        d = check_action(_agent(), _chain(delegation_expires_at=_future()), _ctx())
        assert d.result == ALLOWED

    def test_no_expiry_does_not_block(self):
        d = check_action(_agent(), _chain(delegation_expires_at=None), _ctx())
        assert d.result == ALLOWED

    def test_naive_datetime_treated_as_utc(self):
        # a naive datetime (no tzinfo) in the past must still be caught
        naive_past = datetime.utcnow() - timedelta(minutes=5)
        d = check_action(_agent(), _chain(delegation_expires_at=naive_past), _ctx())
        assert d.result == DENIED
        assert d.incident_type == "delegation_expired"

    def test_expiry_blocks_even_with_valid_capabilities(self):
        # capabilities are fine, but the delegation has expired -> still denied
        d = check_action(
            _agent(),
            _chain(delegation_expires_at=_past(), granted_capabilities=["read_analytics"]),
            _ctx(),
        )
        assert d.result == DENIED
        assert d.incident_type == "delegation_expired"
