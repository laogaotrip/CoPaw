# -*- coding: utf-8 -*-
"""Unit tests for autonomy-level behavior in ToolGuardMixin."""

from __future__ import annotations

from types import SimpleNamespace

from copaw.agents.tool_guard_mixin import ToolGuardMixin


class _DummyAgent(ToolGuardMixin):
    def __init__(self, level: str, session_id: str) -> None:
        self._agent_config = SimpleNamespace(
            autonomy=SimpleNamespace(level=level),
        )
        self._request_context = {"session_id": session_id}


def test_should_require_approval_for_l3_with_session() -> None:
    agent = _DummyAgent(level="L3", session_id="s1")
    assert agent._get_autonomy_level() == "L3"
    assert agent._should_require_approval() is True


def test_should_not_require_approval_for_l2() -> None:
    agent = _DummyAgent(level="L2", session_id="s1")
    assert agent._get_autonomy_level() == "L2"
    assert agent._should_require_approval() is False


def test_should_not_require_approval_without_session() -> None:
    agent = _DummyAgent(level="L3", session_id="")
    assert agent._should_require_approval() is False

