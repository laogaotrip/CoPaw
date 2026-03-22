# -*- coding: utf-8 -*-
"""Unit tests for MCP preset discovery helpers."""

from __future__ import annotations

from copaw.app.routers.mcp import _preset_catalog


def test_preset_catalog_contains_expected_keys() -> None:
    presets = _preset_catalog()
    keys = {p.key for p in presets}
    assert "filesystem" in keys
    assert "fetch" in keys
    assert "github" in keys

