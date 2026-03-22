# -*- coding: utf-8 -*-
"""Unit tests for channel manager send retry helper."""

from __future__ import annotations

import pytest

from copaw.app.channels.manager import ChannelManager


@pytest.mark.asyncio
async def test_send_with_retries_succeeds_after_retry() -> None:
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary")

    await ChannelManager._send_with_retries(
        operation="send_event",
        channel_name="dummy",
        retries=1,
        backoff_ms=0,
        func=flaky,
    )
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_send_with_retries_raises_after_exhausted() -> None:
    async def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await ChannelManager._send_with_retries(
            operation="send_event",
            channel_name="dummy",
            retries=1,
            backoff_ms=0,
            func=always_fail,
        )

