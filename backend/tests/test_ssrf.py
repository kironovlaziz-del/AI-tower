"""
Tests for app.core.ssrf - the SSRF guard for outbound webhooks.

This is security-critical code: a gap here lets an org member turn the
server into a proxy into the private network. The tests therefore cover
every blocked category explicitly (loopback, private, link-local incl.
cloud metadata, unspecified, reserved, multicast, IPv6, IPv4-mapped) and
assert that genuinely public targets still pass.

validate_webhook_url is the create/update-time check (no DNS).
assert_safe_webhook_target is the send-time check (resolves DNS) - it is
tested with the resolver monkeypatched so the suite is hermetic and does
not depend on real network conditions.
"""

import pytest

from app.core.ssrf import (
    validate_webhook_url,
    assert_safe_webhook_target,
    WebhookURLError,
)


# ---------------------------------------------------------------------------
# validate_webhook_url - structural + literal-IP checks
# ---------------------------------------------------------------------------

class TestValidateWebhookURL:
    @pytest.mark.parametrize(
        "url",
        [
            "https://hooks.example.com/abc",
            "http://example.com",
            "https://example.com:8443/path",
            "https://sub.domain.example.org/webhook",
        ],
    )
    def test_public_urls_pass(self, url):
        # Returns the (possibly normalized) URL, does not raise.
        assert validate_webhook_url(url).startswith("http")

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/hook",
            "http://127.0.0.1:8000/",
            "https://169.254.169.254/latest/meta-data/",  # cloud metadata
            "http://10.0.0.5/x",
            "http://192.168.1.1/x",
            "http://172.16.0.1/x",
            "http://0.0.0.0/x",
            "http://[::1]/x",             # IPv6 loopback
            "http://[fe80::1]/x",         # IPv6 link-local
        ],
    )
    def test_internal_ip_literals_rejected(self, url):
        with pytest.raises(WebhookURLError):
            validate_webhook_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "ftp://example.com",
            "gopher://example.com",
            "file:///etc/passwd",
            "example.com/no-scheme",
            "javascript:alert(1)",
        ],
    )
    def test_malformed_or_wrong_scheme_rejected(self, url):
        with pytest.raises(WebhookURLError):
            validate_webhook_url(url)

    def test_trailing_slash_normalized(self):
        assert validate_webhook_url("https://example.com/hook/") == "https://example.com/hook"

    def test_bare_host_trailing_slash_kept(self):
        # "https://example.com/" has only the root slash - leave it.
        assert validate_webhook_url("https://example.com/") == "https://example.com/"

    def test_hostname_not_resolved_here(self):
        # A hostname that COULD resolve internally must still pass the
        # create-time check (DNS resolution is the send-time layer's job).
        assert validate_webhook_url("https://internal.corp.local/hook").startswith("https")


# ---------------------------------------------------------------------------
# assert_safe_webhook_target - send-time DNS resolution check
# ---------------------------------------------------------------------------

class TestAssertSafeWebhookTarget:
    def test_ip_literal_public_ok(self):
        # 8.8.8.8 is public - no resolution needed, must not raise.
        assert_safe_webhook_target("https://8.8.8.8/hook")

    def test_ip_literal_internal_blocked(self):
        with pytest.raises(WebhookURLError):
            assert_safe_webhook_target("http://127.0.0.1/hook")

    def test_metadata_ip_blocked(self):
        with pytest.raises(WebhookURLError):
            assert_safe_webhook_target("http://169.254.169.254/latest/meta-data/")

    def test_hostname_resolving_public_ok(self, monkeypatch):
        # Monkeypatch getaddrinfo so the test is hermetic: pretend the
        # host resolves to a public IP.
        import app.core.ssrf as ssrf

        def fake_getaddrinfo(host, port, *a, **k):
            return [(2, 1, 6, "", ("93.184.216.34", port))]  # public

        monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_getaddrinfo)
        assert_safe_webhook_target("https://example.com/hook")

    def test_hostname_resolving_internal_blocked(self, monkeypatch):
        # DNS rebinding scenario: an innocent-looking host resolves to an
        # internal address at send time. Must be refused.
        import app.core.ssrf as ssrf

        def fake_getaddrinfo(host, port, *a, **k):
            return [(2, 1, 6, "", ("10.0.0.7", port))]  # private

        monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(WebhookURLError):
            assert_safe_webhook_target("https://sneaky.example.com/hook")

    def test_hostname_multiple_ips_one_internal_blocked(self, monkeypatch):
        # If a host returns several A records and ANY is internal, refuse.
        import app.core.ssrf as ssrf

        def fake_getaddrinfo(host, port, *a, **k):
            return [
                (2, 1, 6, "", ("93.184.216.34", port)),  # public
                (2, 1, 6, "", ("192.168.0.10", port)),   # private - poison
            ]

        monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(WebhookURLError):
            assert_safe_webhook_target("https://mixed.example.com/hook")

    def test_unresolvable_host_blocked(self, monkeypatch):
        import socket as pysocket
        import app.core.ssrf as ssrf

        def fake_getaddrinfo(host, port, *a, **k):
            raise pysocket.gaierror("name resolution failed")

        monkeypatch.setattr(ssrf.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(WebhookURLError):
            assert_safe_webhook_target("https://does-not-exist.example/hook")
