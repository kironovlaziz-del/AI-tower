"""
Tests for app.core.agent_signing - Ed25519 signing/verification that
underpins the whole agent-governance accountability guarantee.

If verification could be fooled (tampered payload, wrong key, swapped
fields), the "verifiable delegation chain" property collapses - so these
cover tamper, wrong-key, and canonicalization explicitly, not just the
happy path. Pure crypto, no DB.
"""

import pytest

from app.core.agent_signing import (
    generate_keypair,
    canonical_bytes,
    sign_payload,
    verify_payload,
)


class TestKeypair:
    def test_generates_distinct_base64_keys(self):
        priv, pub = generate_keypair()
        assert isinstance(priv, str) and isinstance(pub, str)
        assert priv != pub
        # a second keypair must differ
        priv2, pub2 = generate_keypair()
        assert pub != pub2


class TestSignVerify:
    def test_valid_signature_verifies(self):
        priv, pub = generate_keypair()
        payload = {"chain_id": 5, "agent_id": 3, "tool": "openai.chat"}
        sig = sign_payload(payload, priv)
        assert verify_payload(payload, sig, pub) is True

    def test_tampered_payload_fails(self):
        priv, pub = generate_keypair()
        payload = {"model": "gpt-4o-mini", "amount": 10}
        sig = sign_payload(payload, priv)
        tampered = dict(payload, amount=1000000)
        assert verify_payload(tampered, sig, pub) is False

    def test_wrong_public_key_fails(self):
        priv, _ = generate_keypair()
        _, other_pub = generate_keypair()
        payload = {"x": 1}
        sig = sign_payload(payload, priv)
        assert verify_payload(payload, sig, other_pub) is False

    def test_field_reorder_still_verifies(self):
        # Canonicalization sorts keys, so key order in the dict must not
        # matter for verification.
        priv, pub = generate_keypair()
        sig = sign_payload({"a": 1, "b": 2}, priv)
        assert verify_payload({"b": 2, "a": 1}, sig, pub) is True

    def test_added_field_fails(self):
        priv, pub = generate_keypair()
        sig = sign_payload({"a": 1}, priv)
        assert verify_payload({"a": 1, "b": 2}, sig, pub) is False


class TestCanonicalization:
    def test_key_order_independent(self):
        assert canonical_bytes({"a": 1, "b": 2}) == canonical_bytes({"b": 2, "a": 1})

    def test_no_incidental_whitespace(self):
        # Deterministic separators - no spaces that could vary.
        assert b" " not in canonical_bytes({"a": "x", "b": "y"})


class TestMalformedInputs:
    def test_bad_signature_returns_false_not_raise(self):
        _, pub = generate_keypair()
        assert verify_payload({"a": 1}, "not-base64!!!", pub) is False

    def test_bad_public_key_returns_false(self):
        priv, _ = generate_keypair()
        sig = sign_payload({"a": 1}, priv)
        assert verify_payload({"a": 1}, sig, "garbage") is False

    def test_empty_signature_or_key_returns_false(self):
        priv, pub = generate_keypair()
        sig = sign_payload({"a": 1}, priv)
        assert verify_payload({"a": 1}, "", pub) is False
        assert verify_payload({"a": 1}, sig, "") is False
