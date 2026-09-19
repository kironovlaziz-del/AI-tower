"""
Runtime policy engine for agent actions.

Given an agent, the chain it's acting in, and the action it wants to
perform, decide allowed / denied / pending_approval. This is the
gatekeeper every tool/model call passes through.

The check order (cheapest and most fundamental first):
  1. tool allowed for this agent?
  2. model allowed (for model-invoking tools)?
  3. delegation depth within the agent's limit?
  4. the action's capabilities still a subset of the chain's granted set
     (no escalation mid-chain)?
  5. custom agent policies (JSON rules) - evaluated last, can only
     further restrict.

Returns a Decision (dataclass) with the verdict, a human reason, and -
when denied by escalation/depth - an incident_type so the caller can
raise the right AgentIncident. Pure decision logic: it does NOT write to
the DB (the caller records the action and any incident), which keeps it
unit-testable without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.capability_validator import escalated_items


ALLOWED = "allowed"
DENIED = "denied"
PENDING_APPROVAL = "pending_approval"


@dataclass
class Decision:
    result: str
    reason: str
    incident_type: Optional[str] = None  # capability_escalation | depth_exceeded | policy_violation
    matched_policy_id: Optional[int] = None


@dataclass
class ActionContext:
    """Everything the engine needs, passed in by the caller so the engine
    itself stays DB-free."""
    tool_name: Optional[str]
    action_type: Optional[str]
    input_data: Dict[str, Any] = field(default_factory=dict)
    # the capabilities this action requires/claims (subset check target)
    action_capabilities: List[str] = field(default_factory=list)


@dataclass
class AgentView:
    """The subset of Agent fields the engine reads (again, so it can be
    tested with plain objects, not ORM rows)."""
    allowed_tools: List[str] = field(default_factory=list)
    allowed_models: List[str] = field(default_factory=list)
    max_delegation_depth: int = 3
    status: str = "active"


@dataclass
class ChainView:
    max_depth_reached: int = 0
    granted_capabilities: List[str] = field(default_factory=list)


# Tools that invoke a model and therefore trigger the model-allowlist
# check. Kept explicit rather than guessed from the name.
_MODEL_INVOKING_TOOLS = {"openai.chat", "anthropic.messages", "model.invoke", "llm.chat"}


def evaluate_custom_rule(rule: Dict[str, Any], ctx: ActionContext) -> bool:
    """
    Evaluate one custom JSON policy rule against the action. Returns True
    if the action SATISFIES the rule (is allowed by it), False if it
    violates it.

    Supported rule shapes (intentionally small and explicit - not a
    turing-complete expression evaluator, which would be a security and
    maintenance hazard):

      {"deny_tools": ["stripe.charge", ...]}
          -> violated if the action's tool is in the list
      {"allow_only_tools": ["openai.chat", ...]}
          -> violated if the action's tool is NOT in the list
      {"deny_action_types": ["api_request"]}
          -> violated if action_type is in the list

    Unknown rule keys are ignored (fail-open for the rule itself), so a
    typo can't silently block everything - but see the engine, which
    treats a rule returning False as a denial.
    """
    tool = ctx.tool_name
    if "deny_tools" in rule:
        if tool in set(rule.get("deny_tools") or []):
            return False
    if "allow_only_tools" in rule:
        if tool not in set(rule.get("allow_only_tools") or []):
            return False
    if "deny_action_types" in rule:
        if ctx.action_type in set(rule.get("deny_action_types") or []):
            return False
    return True


def check_action(
    agent: AgentView,
    chain: ChainView,
    ctx: ActionContext,
    custom_policies: Optional[List[Dict[str, Any]]] = None,
) -> Decision:
    # 0. agent must be active
    if agent.status != "active":
        return Decision(DENIED, f"Agent is {agent.status}, not active", "policy_violation")

    # 1. tool allowlist
    if ctx.tool_name and ctx.tool_name not in set(agent.allowed_tools or []):
        return Decision(DENIED, f"Tool '{ctx.tool_name}' is not in the agent's allowed tools",
                        "policy_violation")

    # 2. model allowlist (only for model-invoking tools)
    if ctx.tool_name in _MODEL_INVOKING_TOOLS:
        model = ctx.input_data.get("model")
        if model and model not in set(agent.allowed_models or []):
            return Decision(DENIED, f"Model '{model}' is not in the agent's allowed models",
                            "policy_violation")

    # 3. delegation depth
    if chain.max_depth_reached > agent.max_delegation_depth:
        return Decision(DENIED, "Delegation depth exceeded", "depth_exceeded")

    # 4. capability escalation (action must stay within the chain grant)
    escalated = escalated_items(ctx.action_capabilities, chain.granted_capabilities)
    if escalated:
        return Decision(
            DENIED,
            f"Capability escalation detected: {', '.join(escalated)}",
            "capability_escalation",
        )

    # 5. custom policies (can only further restrict)
    for policy in custom_policies or []:
        rules = policy.get("rules") or {}
        # rules can be a single rule dict or a list of them
        rule_list = rules if isinstance(rules, list) else [rules]
        for rule in rule_list:
            if not evaluate_custom_rule(rule, ctx):
                return Decision(
                    DENIED,
                    f"Blocked by policy '{policy.get('name', policy.get('id'))}'",
                    "policy_violation",
                    matched_policy_id=policy.get("id"),
                )

    return Decision(ALLOWED, "Action permitted")
