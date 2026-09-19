"""
SSRF protection for outbound webhooks.

A webhook target is a URL the server will POST to. Without checks, an
org member who can create a notification channel could point it at
internal infrastructure the server can reach but they cannot -
127.0.0.1, 169.254.169.254 (cloud instance metadata!), 10.x/172.16.x/
192.168.x, etc. - and use the server as a proxy into the private network
(classic SSRF).

Defense is in two layers, because neither alone is enough:

1. validate_webhook_url() - called at create/update time. Rejects
   non-http(s) schemes, missing host, and hostnames that are literal
   private/loopback/link-local IPs. This gives the user an immediate,
   clear error for the obvious cases.

2. assert_safe_webhook_target() - called RIGHT BEFORE the request is
   sent. Resolves the hostname to its actual IP(s) and refuses if any
   resolve into a blocked range. This is the layer that matters most: it
   catches a hostname that looked innocent at create time but resolves
   to an internal address (including deliberate DNS rebinding, where the
   name resolves differently between validation and send).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class WebhookURLError(ValueError):
    """Raised when a webhook URL is malformed or points at a disallowed
    (internal/private) address."""


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    """True if this IP must never be a webhook target. Covers loopback,
    private ranges, link-local (incl. 169.254.169.254 metadata),
    unspecified (0.0.0.0), reserved and multicast - for both IPv4 and
    IPv6, and IPv4-mapped IPv6 addresses."""
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) so it's judged as
    # the IPv4 address it really targets.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_multicast
    )


def validate_webhook_url(url: str) -> str:
    """
    Structural + literal-IP validation, for create/update time. Returns
    the normalized URL or raises WebhookURLError. Does NOT resolve DNS
    (that's the send-time layer) - it only rejects obviously bad URLs and
    hostnames that are themselves private IP literals.
    """
    url = url.strip()
    if not url:
        raise WebhookURLError("webhook URL must not be empty")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise WebhookURLError("webhook URL must start with http:// or https://")
    if not parsed.hostname:
        raise WebhookURLError("webhook URL must include a host")

    # If the host is a literal IP, reject blocked ranges immediately.
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        ip = None  # it's a hostname, checked at send time
    if ip is not None and _ip_is_blocked(ip):
        raise WebhookURLError(
            "webhook URL points at a private, loopback, or link-local address"
        )

    # Normalize a trailing slash on a real path so /hook and /hook/ are
    # one target - but keep the lone root slash ("https://host/"), which
    # is just the empty path.
    if parsed.path not in ("", "/") and url.endswith("/"):
        url = url.rstrip("/")
    return url


def assert_safe_webhook_target(url: str) -> None:
    """
    Send-time guard: resolve the URL's host and refuse if ANY resolved
    address is in a blocked range. Raises WebhookURLError on violation or
    if the host cannot be resolved. Call this immediately before issuing
    the HTTP request.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise WebhookURLError("webhook URL has no host")

    # If host is already an IP literal, check it directly.
    try:
        ip = ipaddress.ip_address(host)
        if _ip_is_blocked(ip):
            raise WebhookURLError("webhook target resolves to a blocked address")
        return
    except ValueError:
        pass  # hostname - resolve it

    try:
        # getaddrinfo returns every A/AAAA record; a hostname could map to
        # several IPs, and we must reject if ANY of them is internal.
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise WebhookURLError(f"could not resolve webhook host '{host}'") from exc

    for family, _type, _proto, _canon, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _ip_is_blocked(ip):
            raise WebhookURLError(
                f"webhook host '{host}' resolves to a blocked address ({ip_str})"
            )
