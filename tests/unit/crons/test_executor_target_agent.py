# -*- coding: utf-8 -*-
"""Unit tests for cron executor cross-agent routing."""

from __future__ import annotations

import pytest

from copaw.app.crons.executor import CronExecutor
from copaw.app.crons.models import CronJobRequest, CronJobSpec


class _DummyRunner:
    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.calls = []

    async def stream_query(self, req):
        self.calls.append(req)
        yield {"type": "delta", "marker": self.marker}


class _DummyWorkspace:
    def __init__(self, runner) -> None:
        self.runner = runner


class _DummyManager:
    def __init__(self, workspace) -> None:
        self.workspace = workspace
        self.requested_agent_ids = []

    async def get_agent(self, agent_id: str):
        self.requested_agent_ids.append(agent_id)
        return self.workspace


class _DummyChannelManager:
    def __init__(self) -> None:
        self.events = []

    async def send_event(
        self,
        *,
        channel,
        user_id,
        session_id,
        event,
        meta,
    ) -> None:
        self.events.append(
            {
                "channel": channel,
                "user_id": user_id,
                "session_id": session_id,
                "event": event,
                "meta": meta,
            },
        )

    async def send_text(self, **_kwargs) -> None:
        raise AssertionError("send_text should not be called for agent task")


def _build_agent_job(meta=None) -> CronJobSpec:
    return CronJobSpec(
        id="job-1",
        name="agent-job",
        enabled=True,
        schedule={"type": "cron", "cron": "0 9 * * *", "timezone": "UTC"},
        task_type="agent",
        request=CronJobRequest(input="hello"),
        dispatch={
            "type": "channel",
            "channel": "feishu",
            "target": {"user_id": "u1", "session_id": "s1"},
            "mode": "stream",
            "meta": meta or {},
        },
    )


@pytest.mark.asyncio
async def test_execute_agent_uses_current_runner_when_no_target_agent() -> None:
    current_runner = _DummyRunner("current")
    channel_manager = _DummyChannelManager()
    executor = CronExecutor(runner=current_runner, channel_manager=channel_manager)
    job = _build_agent_job()

    await executor.execute(job)

    assert len(current_runner.calls) == 1
    assert current_runner.calls[0]["source"] == "cron"
    assert len(channel_manager.events) == 1
    assert channel_manager.events[0]["event"]["marker"] == "current"


@pytest.mark.asyncio
async def test_execute_agent_routes_to_target_agent_runner_when_configured() -> None:
    current_runner = _DummyRunner("current")
    target_runner = _DummyRunner("target")
    manager = _DummyManager(_DummyWorkspace(target_runner))
    current_runner._manager = manager  # pylint: disable=protected-access

    channel_manager = _DummyChannelManager()
    executor = CronExecutor(runner=current_runner, channel_manager=channel_manager)
    job = _build_agent_job(meta={"target_agent_id": "agent-b"})

    await executor.execute(job)

    assert manager.requested_agent_ids == ["agent-b"]
    assert len(target_runner.calls) == 1
    assert target_runner.calls[0]["source"] == "cron"
    assert len(current_runner.calls) == 0
    assert len(channel_manager.events) == 1
    assert channel_manager.events[0]["event"]["marker"] == "target"

