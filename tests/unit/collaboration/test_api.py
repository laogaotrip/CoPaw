# -*- coding: utf-8 -*-
"""Unit tests for collaboration API helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from copaw.app.collaboration.api import get_events, get_stats


@pytest.mark.asyncio
async def test_get_events_forwards_filters_to_service() -> None:
    svc = Mock()
    svc.list_events.return_value = [{"mode": "notify"}]

    result = await get_events(
        limit=20,
        mode="notify",
        target_agent_id="agent-b",
        svc=svc,
    )

    assert result == {"events": [{"mode": "notify"}]}
    svc.list_events.assert_called_once_with(
        limit=20,
        mode="notify",
        target_agent_id="agent-b",
    )


@pytest.mark.asyncio
async def test_get_stats_forwards_window_to_service() -> None:
    svc = Mock()
    svc.get_stats.return_value = {"total": 1}

    result = await get_stats(
        since_hours=48,
        svc=svc,
    )

    assert result == {"total": 1}
    svc.get_stats.assert_called_once_with(since_hours=48)
