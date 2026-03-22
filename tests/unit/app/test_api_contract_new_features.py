# -*- coding: utf-8 -*-
"""API contract tests for newly added digital-employee endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from copaw.app.crons.api import get_audit_events, get_audit_stats
from copaw.app.routers.config import get_triggers, put_triggers
from copaw.config.config import AgentTriggerPolicyConfig


@pytest.mark.asyncio
async def test_get_triggers_returns_agent_trigger_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = AgentTriggerPolicyConfig(
        enable_webhook=True,
        enable_poll=False,
        block_private_network=True,
        allowed_poll_domains=["example.com"],
    )
    agent = SimpleNamespace(config=SimpleNamespace(triggers=policy))

    async def _fake_get_agent(_request):
        return agent

    monkeypatch.setattr(
        "copaw.app.agent_context.get_agent_for_request",
        _fake_get_agent,
    )

    result = await get_triggers(request=SimpleNamespace())
    assert result == policy
    assert result.enable_poll is False
    assert result.allowed_poll_domains == ["example.com"]


@pytest.mark.asyncio
async def test_put_triggers_persists_and_returns_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = AgentTriggerPolicyConfig(
        enable_webhook=False,
        enable_poll=False,
        block_private_network=True,
        allowed_poll_domains=["api.example.com"],
    )
    agent = SimpleNamespace(
        agent_id="agent-a",
        config=SimpleNamespace(triggers=AgentTriggerPolicyConfig()),
    )

    async def _fake_get_agent(_request):
        return agent

    save_calls = []

    def _fake_save_agent_config(agent_id, cfg):
        save_calls.append((agent_id, cfg))

    monkeypatch.setattr(
        "copaw.app.agent_context.get_agent_for_request",
        _fake_get_agent,
    )
    monkeypatch.setattr(
        "copaw.config.config.save_agent_config",
        _fake_save_agent_config,
    )

    result = await put_triggers(
        request=SimpleNamespace(),
        body=policy,
    )

    assert result == policy
    assert save_calls and save_calls[0][0] == "agent-a"
    assert agent.config.triggers.enable_webhook is False


@pytest.mark.asyncio
async def test_cron_audit_api_contract_keys() -> None:
    mgr = Mock()
    mgr.list_audit_events.return_value = [{"job_id": "job-a"}]
    mgr.get_audit_stats.return_value = {
        "total": 1,
        "by_status": {"success": 1},
        "by_trigger_type": {"cron": 1},
        "since_hours": 24,
    }

    events = await get_audit_events(
        limit=20,
        job_id="",
        status="",
        trigger_type="",
        mgr=mgr,
    )
    stats = await get_audit_stats(
        since_hours=24,
        mgr=mgr,
    )

    assert "events" in events and isinstance(events["events"], list)
    assert {"total", "by_status", "by_trigger_type", "since_hours"} <= set(
        stats.keys(),
    )

