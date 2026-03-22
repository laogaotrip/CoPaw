# -*- coding: utf-8 -*-
"""Tests for agent model slot resolution logic."""

from __future__ import annotations

from copaw.providers.models import ModelSlotConfig
from copaw.agents.model_factory import resolve_agent_model_slots


class _DummyAgentConfig:
    def __init__(
        self,
        *,
        active_model=None,
        primary_model=None,
        fallback_model=None,
    ) -> None:
        self.active_model = active_model
        self.primary_model = primary_model
        self.fallback_model = fallback_model


def test_primary_and_fallback_are_used_when_present() -> None:
    cfg = _DummyAgentConfig(
        active_model=ModelSlotConfig(provider_id="openai", model="gpt-4"),
        primary_model=ModelSlotConfig(provider_id="openai", model="gpt-5"),
        fallback_model=ModelSlotConfig(
            provider_id="anthropic",
            model="claude-3-5-sonnet-20241022",
        ),
    )

    primary, fallback = resolve_agent_model_slots(cfg)
    assert primary is not None
    assert fallback is not None
    assert primary.model == "gpt-5"
    assert fallback.model == "claude-3-5-sonnet-20241022"


def test_active_model_is_back_compat_primary_when_primary_missing() -> None:
    cfg = _DummyAgentConfig(
        active_model=ModelSlotConfig(provider_id="openai", model="gpt-4o"),
        primary_model=None,
        fallback_model=None,
    )

    primary, fallback = resolve_agent_model_slots(cfg)
    assert primary is not None
    assert fallback is None
    assert primary.model == "gpt-4o"
