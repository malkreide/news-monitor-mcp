"""Inbound Host/Origin validation on the HTTP transport (SEC-005, inbound half).

The SDK leaves DNS-rebinding protection off while ``transport_security`` is
unset. This server never set it, so there was no Host check at all. These tests
pin the new behaviour and fail if the protection is dropped again.
"""

from __future__ import annotations

import pytest

from news_monitor_mcp.server import build_transport_security


def test_loopback_bind_enables_protection(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000, frozenset())
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts
    assert "localhost:8000" in sec.allowed_hosts


def test_non_local_bind_without_allowlist_stays_off(monkeypatch):
    """0.0.0.0 with no allow-list: the reachable name is unknowable here, so a
    guess would reject every real request. Protection stays off; caller warns."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security("0.0.0.0", 8000, frozenset()) is None


def test_non_local_bind_with_allowlist_enables_protection(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.ch,mcp.example.ch:443")
    sec = build_transport_security("0.0.0.0", 8000, frozenset())
    assert sec is not None
    assert "mcp.example.ch" in sec.allowed_hosts
    # Loopback stays in, otherwise container health checks break.
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_port_is_honoured(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 9443, frozenset())
    assert "127.0.0.1:9443" in sec.allowed_hosts
    assert "127.0.0.1:8000" not in sec.allowed_hosts


def test_derived_loopback_origins_are_present(monkeypatch):
    """An empty allowed_origins would refuse a same-host browser request: the
    SDK only skips the Origin check when the header is absent entirely."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000, frozenset())
    assert "http://127.0.0.1:8000" in sec.allowed_origins


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_all_loopback_forms_are_local(host, monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert build_transport_security(host, 8000, frozenset()) is not None


def test_configured_origins_pass_and_wildcard_is_not_copied(monkeypatch):
    """Allowed origins must also pass the transport check, or the server would
    refuse exactly the browser clients CORS permits. "*" is matched literally by
    the SDK, so copying it would look like a wildcard while doing nothing."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    sec = build_transport_security("127.0.0.1", 8000, frozenset({"https://claude.ai", "*"}))
    assert "https://claude.ai" in sec.allowed_origins
    assert "*" not in sec.allowed_origins
