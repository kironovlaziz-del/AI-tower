# Copyright (c) 2026 Laziz Kironov
# Licensed under the Apache License, Version 2.0.
# Part of Provenza — https://github.com/kironovlaziz-del/provenza

"""
Capability validation for delegation - the core anti-escalation check.

The governance guarantee is: an agent can never delegate more than it
holds. When agent A delegates to agent B, B's granted capabilities/tools
must be a SUBSET of what A itself has in this chain. A superset is a
privilege-escalation attempt and must be refused (and raised as an
incident).

Pure functions, no DB - so they're trivially testable and the policy
engine / delegation service can call them freely.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple


def _as_set(items: Optional[Iterable[str]]) -> set:
    if not items:
        return set()
    return {str(x) for x in items}


def is_subset(child: Optional[Iterable[str]], parent: Optional[Iterable[str]]) -> bool:
    """True if every capability/tool in `child` is also in `parent`.
    An empty child is trivially a subset (delegating nothing is fine)."""
    return _as_set(child).issubset(_as_set(parent))


def escalated_items(
    child: Optional[Iterable[str]], parent: Optional[Iterable[str]]
) -> List[str]:
    """The items the child was granted that the parent does not hold -
    i.e. the escalation. Empty list means no escalation. Sorted for
    stable output/logging."""
    return sorted(_as_set(child) - _as_set(parent))


def validate_delegation(
    delegated_capabilities: Optional[Iterable[str]],
    parent_capabilities: Optional[Iterable[str]],
) -> Tuple[bool, List[str]]:
    """
    Validate a single delegation step. Returns (ok, escalated):
      ok=True, [] -> the delegation stays within the parent's rights
      ok=False, [...] -> escalation detected; the list is the offending
                         capabilities, for the incident details.
    """
    escalated = escalated_items(delegated_capabilities, parent_capabilities)
    return (len(escalated) == 0, escalated)


def effective_capabilities_for_hop(
    delegated_capabilities: Optional[Iterable[str]],
    parent_capabilities: Optional[Iterable[str]],
) -> List[str]:
    """
    What the child actually ends up with: the intersection of what was
    delegated and what the parent could legally give. Even if a caller
    tries to over-delegate, this clamps the result to the safe subset -
    a defense-in-depth companion to validate_delegation (which rejects),
    used where we prefer to clamp rather than fail.
    """
    return sorted(_as_set(delegated_capabilities) & _as_set(parent_capabilities))
