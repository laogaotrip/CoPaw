# -*- coding: utf-8 -*-
"""Unit tests for cross-agent collaboration service."""

from __future__ import annotations

import pytest

from copaw.app.collaboration.service import (
    CollaborationError,
    CollaborationService,
)


class _DummyRunner:
    def __init__(self, events):
        self.events = events
        self.calls = []

    async def stream_query(self, req):
        self.calls.append(req)
        for event in self.events:
            yield event


class _DummyChannelManager:
    def __init__(self) -> None:
        self.sent = []

    async def send_text(
        self,
        *,
        channel,
        user_id,
        session_id,
        text,
        meta,
    ) -> None:
        self.sent.append(
            {
                "channel": channel,
                "user_id": user_id,
                "session_id": session_id,
                "text": text,
                "meta": meta,
            },
        )


class _DummyWorkspace:
    def __init__(self, *, agent_id: str, runner=None, channel_manager=None):
        self.agent_id = agent_id
        self.runner = runner
        self.channel_manager = channel_manager
        self.workspace_dir = "/tmp"


class _DummyManager:
    def __init__(self, target_workspace):
        self._target_workspace = target_workspace
        self.requested = []

    async def get_agent(self, agent_id: str):
        self.requested.append(agent_id)
        return self._target_workspace


@pytest.mark.asyncio
async def test_consult_routes_to_target_agent_and_returns_text() -> None:
    target_runner = _DummyRunner(
        [
            {"type": "delta", "text": "part-1"},
            {"type": "delta", "text": "part-2"},
        ],
    )
    target_workspace = _DummyWorkspace(agent_id="agent-b", runner=target_runner)
    manager = _DummyManager(target_workspace)
    source_workspace = _DummyWorkspace(agent_id="agent-a")
    source_workspace._manager = manager  # pylint: disable=protected-access
    service = CollaborationService(source_workspace)

    result = await service.consult(
        target_agent_id="agent-b",
        prompt="help me",
        user_id="u1",
        session_id="s1",
    )

    assert result.target_agent_id == "agent-b"
    assert "part-1" in result.response_text
    assert "part-2" in result.response_text
    assert manager.requested == ["agent-b"]
    assert target_runner.calls[0]["source"] == "collaboration"


@pytest.mark.asyncio
async def test_notify_sends_text_to_target_agent_channel_manager() -> None:
    target_channel_manager = _DummyChannelManager()
    target_workspace = _DummyWorkspace(
        agent_id="agent-b",
        runner=_DummyRunner([]),
        channel_manager=target_channel_manager,
    )
    manager = _DummyManager(target_workspace)
    source_workspace = _DummyWorkspace(agent_id="agent-a")
    source_workspace._manager = manager  # pylint: disable=protected-access
    service = CollaborationService(source_workspace)

    await service.notify(
        target_agent_id="agent-b",
        text="deploy done",
        channel="feishu",
        user_id="u1",
        session_id="s1",
    )

    assert len(target_channel_manager.sent) == 1
    sent = target_channel_manager.sent[0]
    assert sent["channel"] == "feishu"
    assert sent["text"] == "deploy done"
    assert sent["meta"]["source_agent_id"] == "agent-a"


@pytest.mark.asyncio
async def test_delegate_rejects_self_target() -> None:
    source_workspace = _DummyWorkspace(agent_id="agent-a")
    source_workspace._manager = _DummyManager(source_workspace)  # pylint: disable=protected-access
    service = CollaborationService(source_workspace)

    with pytest.raises(CollaborationError, match="target_agent_id cannot be self"):
        await service.delegate(
            target_agent_id="agent-a",
            task="run check",
            user_id="u1",
            session_id="s1",
        )


@pytest.mark.asyncio
async def test_delegate_rejects_when_hop_limit_exceeded() -> None:
    source_workspace = _DummyWorkspace(agent_id="agent-a")
    source_workspace._manager = _DummyManager(source_workspace)  # pylint: disable=protected-access
    service = CollaborationService(source_workspace)

    with pytest.raises(CollaborationError, match="delegation hop limit exceeded"):
        await service.delegate(
            target_agent_id="agent-b",
            task="run check",
            user_id="u1",
            session_id="s1",
            hop_count=4,
        )
