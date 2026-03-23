# -*- coding: utf-8 -*-
"""Tests for auth settings persistence and API contract."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from copaw.app import auth as auth_mod
from copaw.app.routers.auth import (
    UpdateAuthSettingsRequest,
    get_auth_settings,
    update_auth_settings,
)


@pytest.fixture
def auth_file(tmp_path):
    """Patch auth file path to a temporary location."""
    path = tmp_path / "auth.json"
    auth_mod.AUTH_FILE = path
    return path


def test_is_auth_enabled_reads_persisted_flag_over_env(
    auth_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COPAW_AUTH_ENABLED", "false")
    auth_mod.set_auth_enabled(True)
    assert auth_mod.is_auth_enabled() is True


def test_set_user_password_creates_default_admin(auth_file) -> None:
    username = auth_mod.set_user_password("secret123")
    assert username == "admin"
    assert auth_mod.has_registered_users() is True
    assert auth_mod.authenticate("admin", "secret123") is not None


@pytest.mark.asyncio
async def test_update_auth_settings_requires_payload(auth_file) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await update_auth_settings(UpdateAuthSettingsRequest())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_auth_settings_persists_enabled_and_password(
    auth_file,
) -> None:
    response = await update_auth_settings(
        UpdateAuthSettingsRequest(
            enabled=True,
            password="new-secret",
        ),
    )

    assert response.enabled is True
    assert response.has_users is True
    assert response.username == "admin"
    assert auth_mod.authenticate("admin", "new-secret") is not None


@pytest.mark.asyncio
async def test_get_auth_settings_reflects_current_state(auth_file) -> None:
    auth_mod.set_auth_enabled(True)
    auth_mod.set_user_password("abc12345")

    res = await get_auth_settings()
    assert res.enabled is True
    assert res.has_users is True
    assert res.username == "admin"


def test_localhost_auth_bypass_disabled_for_proxied_requests(auth_file) -> None:
    auth_mod.set_auth_enabled(True)
    auth_mod.set_user_password("abc12345")

    proxied_request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/api/agent"),
        headers={"x-forwarded-for": "1.2.3.4"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    local_request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/api/agent"),
        headers={},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    assert auth_mod.AuthMiddleware._should_skip_auth(proxied_request) is False
    assert auth_mod.AuthMiddleware._should_skip_auth(local_request) is True
