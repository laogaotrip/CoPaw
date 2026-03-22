# -*- coding: utf-8 -*-
"""Unit tests for cron audit event store/query."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from copaw.app.crons.api import get_audit_events
from copaw.app.crons.manager import CronManager
from copaw.app.crons.repo.json_repo import JsonJobRepository


@pytest.mark.asyncio
async def test_audit_event_list_latest_first_and_filterable(tmp_path: Path) -> None:
    repo = JsonJobRepository(tmp_path / "jobs.json")
    mgr = CronManager(repo=repo, runner=object(), channel_manager=object())

    mgr._append_audit_event(  # pylint: disable=protected-access
        event_type="execute",
        job_id="job-a",
        status="success",
        trigger_type="cron",
        detail={"k": 1},
    )
    mgr._append_audit_event(  # pylint: disable=protected-access
        event_type="execute",
        job_id="job-b",
        status="error",
        trigger_type="poll",
        detail={"k": 2},
    )

    latest = mgr.list_audit_events(limit=1)
    assert len(latest) == 1
    assert latest[0]["job_id"] == "job-b"

    filtered = mgr.list_audit_events(limit=10, status="success", job_id="job-a")
    assert len(filtered) == 1
    assert filtered[0]["trigger_type"] == "cron"


@pytest.mark.asyncio
async def test_get_audit_events_api_forwards_filters() -> None:
    mgr = Mock()
    mgr.list_audit_events.return_value = [{"job_id": "job-a"}]

    result = await get_audit_events(
        limit=20,
        job_id="job-a",
        status="success",
        trigger_type="cron",
        mgr=mgr,
    )

    assert result == {"events": [{"job_id": "job-a"}]}
    mgr.list_audit_events.assert_called_once_with(
        limit=20,
        job_id="job-a",
        status="success",
        trigger_type="cron",
    )
