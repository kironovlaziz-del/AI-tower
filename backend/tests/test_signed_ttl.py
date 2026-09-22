"""
Tests that the delegation TTL is cryptographically protected once it's part
of the signed payload (Stage 2 of the TTL feature): an attacker can't extend
a delegation's lifetime after it was signed. This is what makes the TTL
*verifiable* rather than merely server-enforced.

The delegation payload mirrors what the /delegate endpoint signs.
"""

from app.core.agent_signing import generate_keypair, sign_payload, verify_payload


def _delegation_payload(expires_in):
    """Same shape the /delegate endpoint builds and signs."""
    return {
        "from_agent_id": 1,
        "to_agent_id": 2,
        "task": "analyze",
        "delegated_capabilities": ["read"],
        "chain_id": None,
        "expires_in": expires_in,
    }


class TestSignedTTL:
    def test_signed_ttl_verifies(self):
        priv, pub = generate_keypair()
        payload = _delegation_payload(180)  # 3-minute delegation
        sig = sign_payload(payload, priv)
        assert verify_payload(payload, sig, pub) is True

    def test_extending_ttl_after_signing_fails(self):
        # The core guarantee: sign for 180s, then try to pass it off as a
        # near-permanent delegation. Verification must reject it.
        priv, pub = generate_keypair()
        payload = _delegation_payload(180)
        sig = sign_payload(payload, priv)
        tampered = _delegation_payload(999_999_999)  # ~31 years
        assert verify_payload(tampered, sig, pub) is False

    def test_shrinking_ttl_after_signing_also_fails(self):
        # Any change to the signed TTL breaks the signature, in either
        # direction — the signature pins the exact value.
        priv, pub = generate_keypair()
        payload = _delegation_payload(600)
        sig = sign_payload(payload, priv)
        tampered = _delegation_payload(1)
        assert verify_payload(tampered, sig, pub) is False

    def test_removing_ttl_after_signing_fails(self):
        # Dropping the expires_in field entirely must not verify either.
        priv, pub = generate_keypair()
        payload = _delegation_payload(180)
        sig = sign_payload(payload, priv)
        without_ttl = {k: v for k, v in payload.items() if k != "expires_in"}
        assert verify_payload(without_ttl, sig, pub) is False

    def test_ttl_none_is_signable(self):
        # An unbounded delegation (expires_in=None) is still a valid signed
        # payload — TTL is optional, but if present it's protected.
        priv, pub = generate_keypair()
        payload = _delegation_payload(None)
        sig = sign_payload(payload, priv)
        assert verify_payload(payload, sig, pub) is True
        # and adding a TTL to a payload signed without one fails
        tampered = _delegation_payload(3600)
        assert verify_payload(tampered, sig, pub) is False
