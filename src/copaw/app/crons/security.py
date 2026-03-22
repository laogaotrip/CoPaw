# -*- coding: utf-8 -*-
"""Security helpers for cron trigger guardrails."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from ...config.config import AgentTriggerPolicyConfig


def validate_poll_url(url: str, policy: AgentTriggerPolicyConfig) -> None:
    """Validate poll URL against trigger policy (SSRF guardrails)."""
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("poll_url must use http/https")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise ValueError("poll_url host is required")

    allowed = [d.strip().lower() for d in policy.allowed_poll_domains if d.strip()]
    if allowed and not _host_in_allowlist(host, allowed):
        raise ValueError("poll_url host is not in allowed_poll_domains")

    if not policy.block_private_network:
        return

    if host in {"localhost"}:
        raise ValueError("poll_url private/local network target is blocked")

    maybe_ip = _try_parse_ip(host)
    if maybe_ip is not None:
        if _is_private_or_local(maybe_ip):
            raise ValueError("poll_url private/local network target is blocked")
        return

    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError(f"poll_url host resolve failed: {e}") from e

    for info in infos:
        ip_txt = info[4][0]
        ip = _try_parse_ip(ip_txt)
        if ip is not None and _is_private_or_local(ip):
            raise ValueError("poll_url private/local network target is blocked")


def _host_in_allowlist(host: str, allowed_domains: list[str]) -> bool:
    for domain in allowed_domains:
        if host == domain or host.endswith(f".{domain}"):
            return True
    return False


def _try_parse_ip(value: str):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _is_private_or_local(ip) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
