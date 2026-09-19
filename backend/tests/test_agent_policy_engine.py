"""
Tests for app.services.agent_policy_engine - the runtime gate every agent
action passes. Covers each decision branch (tool/model allowlist,
delegation depth, capability escalation, suspended agent, custom policies)
plus the pending-approval flow and the deny-beats-approval priority.

The engine is DB-free by design (it takes plain view objects), so these
run with no database.
"""

import pytest

from app.services.agent_policy_engine import (
    check_action,
    AgentView,
    ChainView,
    ActionContext,
    evaluate_custom_rule,
    ALLOWED,
    DENIED,
    PENDING_APPROVAL,
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


class TestBasicDecisions:
    def test_allowed_happy_path(self):
        d = check_action(_agent(), _chain(), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics"]))
        assert d.result == ALLOWED

    def test_tool_not_allowed(self):
        d = check_action(_agent(), _chain(), ActionContext("stripe.charge", "tool_call", {}, []))
        assert d.result == DENIED and d.incident_type == "policy_violation"

    def test_model_not_allowed(self):
        d = check_action(_agent(), _chain(), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o"}, []))
        assert d.result == DENIED

    def test_model_check_skipped_for_non_model_tools(self):
        # db.read isn't a model-invoking tool, so a "model" key is ignored.
        d = check_action(_agent(), _chain(), ActionContext("db.read", "tool_call", {"model": "anything"}, ["read_analytics"]))
        assert d.result == ALLOWED

    def test_suspended_agent_denied(self):
        d = check_action(_agent(status="suspended"), _chain(), ActionContext("openai.chat", "tool_call", {}, []))
        assert d.result == DENIED


class TestDepthAndEscalation:
    def test_depth_exceeded(self):
        d = check_action(_agent(max_delegation_depth=2), _chain(max_depth_reached=5), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, []))
        assert d.result == DENIED and d.incident_type == "depth_exceeded"

    def test_capability_escalation(self):
        d = check_action(_agent(), _chain(granted_capabilities=["read_analytics"]), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics", "admin_delete"]))
        assert d.result == DENIED and d.incident_type == "capability_escalation"


class TestCustomPolicies:
    def test_deny_tools(self):
        pol = [{"id": 7, "name": "no-db", "rules": {"deny_tools": ["db.read"]}}]
        d = check_action(_agent(), _chain(), ActionContext("db.read", "tool_call", {}, ["read_analytics"]), pol)
        assert d.result == DENIED and d.matched_policy_id == 7

    def test_allow_only_tools(self):
        pol = [{"id": 8, "name": "chat-only", "rules": {"allow_only_tools": ["openai.chat"]}}]
        assert check_action(_agent(), _chain(), ActionContext("db.read", "tool_call", {}, ["read_analytics"]), pol).result == DENIED
        assert check_action(_agent(), _chain(), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics"]), pol).result == ALLOWED

    def test_require_approval(self):
        pol = [{"id": 9, "name": "gate", "rules": {"require_approval_tools": ["openai.chat"]}}]
        d = check_action(_agent(), _chain(), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics"]), pol)
        assert d.result == PENDING_APPROVAL and d.matched_policy_id == 9

    def test_deny_beats_approval(self):
        pol = [
            {"id": 10, "name": "gate", "rules": {"require_approval_tools": ["openai.chat"]}},
            {"id": 11, "name": "block", "rules": {"deny_tools": ["openai.chat"]}},
        ]
        d = check_action(_agent(), _chain(), ActionContext("openai.chat", "tool_call", {"model": "gpt-4o-mini"}, ["read_analytics"]), pol)
        assert d.result == DENIED and d.matched_policy_id == 11


class TestEvaluateCustomRule:
    def test_deny_tools_rule(self):
        assert evaluate_custom_rule({"deny_tools": ["x"]}, ActionContext("x", "tool_call", {}, [])) == "deny"

    def test_approval_rule(self):
        assert evaluate_custom_rule({"require_approval_tools": ["x"]}, ActionContext("x", "tool_call", {}, [])) == "approval"

    def test_unknown_rule_key_is_ok(self):
        # A typo'd/unknown key must not silently block everything.
        assert evaluate_custom_rule({"whatever": ["x"]}, ActionContext("x", "tool_call", {}, [])) == "ok"
